"""内容制作管线 v2：竞品拆解 → 本地化 → 拍摄脚本 → 分镜 → 视频生成 → 组装

用法：
  # 完整跑（从下载到成片）
  python content_pipeline.py --input project.json

  # 跳过拆解（已有 analysis JSON）
  python content_pipeline.py --input project.json --skip-teardown --analysis ref_analysis.json

  # 断点续跑（从某步骤开始）
  python content_pipeline.py --input project.json --resume-from script

project.json 格式：
  {
    "project_id": "2026-03-05_spring-skincare",
    "topic": "换季补水精华合集",
    "reference_video_url": "https://www.xiaohongshu.com/explore/...",
    "reference_platform": "xhs",
    "brand": "surenxuan",
    "target_platforms": ["xhs", "douyin"],
    "notes": "聚焦 Torriden 和 SKIN1004，突出换季维稳"
  }

步骤：
  1. teardown   — 下载参照视频 + Gemini 拆解
  2. localize   — 品牌本地化（JSON in → JSON out）
  3. script     — 拍摄脚本生成（v2 新增，纯前向执行层）
  4. storyboard — Nano Banana 2 分镜图生成
  5. videogen   — VEO 3.1 视频片段生成
  6. assemble   — ffmpeg 拼接 + Drive 上传
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STEPS = ['teardown', 'localize', 'script', 'storyboard', 'videogen', 'assemble']
WORK_BASE = '/tmp/content-pipeline'


def _load_project(path):
    """Load and validate project.json."""
    with open(path, encoding='utf-8') as f:
        project = json.load(f)

    required = ['project_id', 'reference_video_url']
    for key in required:
        if key not in project:
            raise ValueError(f"project.json missing required key: {key}")

    # Defaults
    project.setdefault('brand', 'surenxuan')
    project.setdefault('reference_platform', 'xhs')
    project.setdefault('target_platforms', ['xhs'])
    project.setdefault('topic', '')
    project.setdefault('notes', '')

    return project


def _load_state(state_path):
    """Load pipeline state or return empty state."""
    if os.path.exists(state_path):
        with open(state_path, encoding='utf-8') as f:
            return json.load(f)
    return {'completed_steps': [], 'artifacts': {}}


def _save_state(state_path, state):
    """Persist pipeline state."""
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _should_run(step, resume_from, state):
    """Determine if a step should run."""
    if resume_from:
        step_idx = STEPS.index(step)
        resume_idx = STEPS.index(resume_from)
        if step_idx < resume_idx:
            return False
    return step not in state.get('completed_steps', [])


def step_teardown(project, work_dir, state, model='gemini-3-flash-preview'):
    """Step 1: Download reference video + Gemini teardown."""
    from download import detect_platform, make_filename, extract_video_info, download_file
    from gemini_analyze import analyze_video

    url = project['reference_video_url']
    platform = project.get('reference_platform') or detect_platform(url)

    # Download
    print("  Downloading reference video...")
    video_url, title, cover_url = extract_video_info(url, platform)
    filename = make_filename(url, platform, title)
    video_path = os.path.join(work_dir, 'reference_video.mp4')
    download_file(video_url, video_path)
    print(f"  Downloaded: {os.path.getsize(video_path) // 1024}KB")

    # Analyze
    print(f"  Analyzing with {model}...")
    analysis = analyze_video(video_path, model=model)

    analysis_path = os.path.join(work_dir, 'reference_analysis.json')
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    timeline_count = len(analysis.get('content_structure', {}).get('timeline', []))
    print(f"  Analysis complete: {timeline_count} timeline segments")

    state['artifacts']['reference_video'] = video_path
    state['artifacts']['reference_analysis'] = analysis_path
    return analysis_path


def step_localize(project, work_dir, state, analysis_path=None):
    """Step 2: Brand localization."""
    from localize import localize

    if not analysis_path:
        analysis_path = state.get('artifacts', {}).get('reference_analysis')
    if not analysis_path or not os.path.exists(analysis_path):
        raise FileNotFoundError("No analysis JSON found. Run teardown first or provide --analysis.")

    brand = project.get('brand', 'surenxuan')
    print(f"  Localizing for brand '{brand}'...")

    result = localize(analysis_path, brand=brand)

    localized_path = os.path.join(work_dir, 'localized_analysis.json')
    with open(localized_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"  Localized analysis saved: {localized_path}")

    state['artifacts']['localized_analysis'] = localized_path
    return localized_path


def step_script(project, work_dir, state):
    """Step 3: Generate shooting script from localized analysis."""
    from shooting_script import generate_script

    localized_path = state.get('artifacts', {}).get('localized_analysis')
    if not localized_path or not os.path.exists(localized_path):
        raise FileNotFoundError("No localized analysis found. Run localize first.")

    brand = project.get('brand', 'surenxuan')
    product_override = project.get('product_override')
    if product_override and not os.path.isabs(product_override):
        product_override = os.path.join(os.path.dirname(localized_path), product_override)
    print(f"  Generating shooting script for brand '{brand}'...")

    script = generate_script(localized_path, brand=brand,
                             product_override_path=product_override)

    script_path = os.path.join(work_dir, 'shooting_script.json')
    with open(script_path, 'w', encoding='utf-8') as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    # v3 uses segments[].shots[], v2 uses flat shots[]
    if 'segments' in script:
        shot_count = sum(len(s.get('shots', [])) for s in script['segments'])
    else:
        shot_count = len(script.get('shots', []))
    print(f"  Shooting script saved: {script_path} ({shot_count} shots)")

    state['artifacts']['shooting_script'] = script_path
    return script_path


def step_storyboard(project, work_dir, state):
    """Step 4: Nano Banana 2 storyboard generation.

    v2 path: reads from shooting_script.json (preferred)
    v1 fallback: reads from localized_analysis.json
    """
    storyboard_dir = os.path.join(work_dir, 'storyboard')

    # v2: Use shooting script if available
    script_path = state.get('artifacts', {}).get('shooting_script')
    if script_path and os.path.exists(script_path):
        from storyboard import generate_storyboard_from_script
        print(f"  Generating storyboard from shooting script (v2)...")
        prompts_log = generate_storyboard_from_script(script_path, storyboard_dir)
    else:
        # v1 fallback
        from storyboard import generate_storyboard
        localized_path = state.get('artifacts', {}).get('localized_analysis')
        if not localized_path or not os.path.exists(localized_path):
            raise FileNotFoundError("No shooting script or localized analysis found.")
        print(f"  Generating storyboard from analysis JSON (v1 fallback)...")
        prompts_log = generate_storyboard(localized_path, storyboard_dir)

    generated = sum(
        1 for p in prompts_log
        if os.path.exists(os.path.join(storyboard_dir, p['output_file']))
    )

    state['artifacts']['storyboard_dir'] = storyboard_dir
    state['artifacts']['storyboard_count'] = generated

    # Pencil 画布预览（storyboard.py v2 自动生成，这里记录路径）
    pen_path = os.path.join(storyboard_dir, 'storyboard.pen')
    if os.path.exists(pen_path):
        state['artifacts']['storyboard_pen'] = pen_path
        print(f"  Pencil preview: {pen_path}")

    return storyboard_dir


def step_videogen(project, work_dir, state):
    """Step 5: VEO 3.1 video generation from storyboard images.

    v2 path: reads from shooting_script.json (preferred)
    v1 fallback: reads from localized_analysis.json
    """
    storyboard_dir = state.get('artifacts', {}).get('storyboard_dir')
    if not storyboard_dir or not os.path.isdir(storyboard_dir):
        raise FileNotFoundError("No storyboard directory found. Run storyboard first.")

    clips_dir = os.path.join(work_dir, 'video_clips')

    # v2: Use shooting script if available
    script_path = state.get('artifacts', {}).get('shooting_script')
    if script_path and os.path.exists(script_path):
        from videogen import generate_video_clips_from_script
        print(f"  Generating video clips from shooting script (v2)...")
        results = generate_video_clips_from_script(script_path, storyboard_dir, clips_dir)
    else:
        # v1 fallback
        from videogen import generate_video_clips
        localized_path = state.get('artifacts', {}).get('localized_analysis')
        if not localized_path or not os.path.exists(localized_path):
            raise FileNotFoundError("No shooting script or localized analysis found.")
        print(f"  Generating video clips from analysis JSON (v1 fallback)...")
        results = generate_video_clips(localized_path, storyboard_dir, clips_dir)

    generated = sum(1 for r in results if r['status'] == 'ok')
    state['artifacts']['clips_dir'] = clips_dir
    state['artifacts']['clips_count'] = generated
    return clips_dir


def step_assemble(project, work_dir, state):
    """Step 5: ffmpeg assembly."""
    from assemble import assemble_clips

    clips_dir = state.get('artifacts', {}).get('clips_dir')
    if not clips_dir or not os.path.isdir(clips_dir):
        raise FileNotFoundError("No video clips directory found. Run videogen first.")

    final_dir = os.path.join(work_dir, 'final')
    output_path = os.path.join(final_dir, 'final.mp4')

    print(f"  Assembling video clips...")
    result = assemble_clips(clips_dir, output_path)

    if result:
        state['artifacts']['final_video'] = result
        return result
    else:
        raise RuntimeError("ffmpeg assembly failed")
    return None


def run_pipeline(project_path, resume_from=None, skip_teardown=False,
                 analysis_path=None, model='gemini-3-flash-preview'):
    """Run the content production pipeline."""
    project = _load_project(project_path)
    project_id = project['project_id']

    work_dir = os.path.join(WORK_BASE, project_id)
    os.makedirs(work_dir, exist_ok=True)

    state_path = os.path.join(work_dir, 'pipeline_state.json')
    state = _load_state(state_path)

    # Copy project.json to work dir
    project_copy = os.path.join(work_dir, 'project.json')
    with open(project_copy, 'w', encoding='utf-8') as f:
        json.dump(project, f, indent=2, ensure_ascii=False)

    print(f"=== Content Pipeline: {project_id} ===")
    print(f"Work dir: {work_dir}")
    print(f"Brand: {project.get('brand', 'surenxuan')}")
    if resume_from:
        print(f"Resuming from: {resume_from}")
    print()

    # If analysis provided externally, register it
    if analysis_path:
        state['artifacts']['reference_analysis'] = os.path.abspath(analysis_path)

    # --- Step 1: Teardown ---
    if not skip_teardown and _should_run('teardown', resume_from, state):
        print("--- [1/6] Teardown: Download + Gemini Analysis ---")
        try:
            step_teardown(project, work_dir, state, model=model)
            state['completed_steps'].append('teardown')
            _save_state(state_path, state)
            print()
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            _save_state(state_path, state)
            return 1
    elif skip_teardown:
        print("--- [1/6] Teardown: SKIPPED (--skip-teardown) ---")
        print()

    # --- Step 2: Localize ---
    if _should_run('localize', resume_from, state):
        print("--- [2/6] Localize: Brand Adaptation ---")
        try:
            step_localize(project, work_dir, state,
                          analysis_path=state.get('artifacts', {}).get('reference_analysis'))
            state['completed_steps'].append('localize')
            _save_state(state_path, state)
            print()
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            _save_state(state_path, state)
            return 1

    # --- Step 3: Shooting Script (v2 新增) ---
    if _should_run('script', resume_from, state):
        print("--- [3/6] Script: Shooting Script Generation ---")
        try:
            step_script(project, work_dir, state)
            state['completed_steps'].append('script')
            _save_state(state_path, state)
            print()
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            _save_state(state_path, state)
            return 1

    # --- Step 4: Storyboard ---
    if _should_run('storyboard', resume_from, state):
        print("--- [4/6] Storyboard: Nano Banana 2 Image Generation ---")
        try:
            step_storyboard(project, work_dir, state)
            state['completed_steps'].append('storyboard')
            _save_state(state_path, state)
            print()
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            _save_state(state_path, state)
            return 1

    # --- Step 5: Video Generation ---
    if _should_run('videogen', resume_from, state):
        print("--- [5/6] Video Generation: VEO 3.1 ---")
        try:
            step_videogen(project, work_dir, state)
            state['completed_steps'].append('videogen')
            _save_state(state_path, state)
            print()
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            _save_state(state_path, state)
            return 1

    # --- Step 6: Assembly ---
    if _should_run('assemble', resume_from, state):
        print("--- [6/6] Assembly: ffmpeg ---")
        try:
            step_assemble(project, work_dir, state)
            state['completed_steps'].append('assemble')
            _save_state(state_path, state)
            print()
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            _save_state(state_path, state)
            return 1

    # --- Sync to Board ---
    try:
        from content_board import sync_drive_to_sheet
        sync_drive_to_sheet(project_id=project_id)
    except Exception:
        pass  # Board sync is best-effort

    # --- Notify ---
    try:
        from slack_review import notify_pipeline_status
        storyboard_count = state.get('artifacts', {}).get('storyboard_count', 0)
        completed = state.get('completed_steps', [])
        notify_pipeline_status(
            project_id,
            'Phase 1',
            'completed',
            f"Steps: {', '.join(completed)} | Storyboard frames: {storyboard_count}"
        )
    except Exception:
        pass  # Slack notification is best-effort

    # --- Summary ---
    _save_state(state_path, state)
    print("=== Pipeline Summary ===")
    print(f"Project: {project_id}")
    print(f"Completed steps: {', '.join(state.get('completed_steps', []))}")
    for key, val in state.get('artifacts', {}).items():
        if isinstance(val, str):
            print(f"  {key}: {val}")
        else:
            print(f"  {key}: {val}")

    return 0


def main():
    parser = argparse.ArgumentParser(description='Content production pipeline')
    parser.add_argument('--input', required=True, help='Path to project.json')
    parser.add_argument('--resume-from', choices=STEPS,
                        help='Resume from a specific step')
    parser.add_argument('--skip-teardown', action='store_true',
                        help='Skip video download + Gemini analysis')
    parser.add_argument('--analysis', default=None,
                        help='Path to existing analysis JSON (use with --skip-teardown)')
    parser.add_argument('--model', default='gemini-3-flash-preview',
                        help='Gemini model for teardown (default: gemini-3-flash-preview)')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        return 1

    return run_pipeline(
        args.input,
        resume_from=args.resume_from,
        skip_teardown=args.skip_teardown,
        analysis_path=args.analysis,
        model=args.model,
    )


if __name__ == '__main__':
    exit(main())
