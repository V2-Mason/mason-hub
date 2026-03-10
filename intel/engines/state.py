"""Scout v2 管道状态管理和断点续跑系统。

每完成一个 Engine 自动写 checkpoint JSON，管道重启时从上次成功的 Engine 接着跑。
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
from datetime import datetime

CHECKPOINT_DIR = Path(__file__).parent / ".checkpoints"

ENGINE_ORDER = ["spider", "query", "media", "insight", "forum", "report"]


@dataclass
class EngineResult:
    engine: str          # "spider" / "query" / "insight" / "media" / "forum" / "report"
    status: str          # "success" / "failed" / "skipped"
    started_at: str
    finished_at: str
    output_file: str = ""  # 产出文件路径
    error: str = ""
    metrics: dict = field(default_factory=dict)  # 每个 engine 的统计数据


@dataclass
class PipelineState:
    run_id: str                           # "2026-03-10T11:00:00"
    date: str                             # "2026-03-10"
    status: str = "running"               # "running" / "completed" / "failed"
    current_engine: str = ""
    completed_engines: list = field(default_factory=list)  # list[EngineResult]

    def save_checkpoint(self):
        """写 JSON 到 .checkpoints/{date}.json"""
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "run_id": self.run_id,
            "date": self.date,
            "status": self.status,
            "current_engine": self.current_engine,
            "completed_engines": [
                asdict(e) if isinstance(e, EngineResult) else e
                for e in self.completed_engines
            ],
            "updated_at": datetime.now().isoformat(),
        }
        checkpoint_path = CHECKPOINT_DIR / f"{self.date}.json"
        checkpoint_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    @classmethod
    def load_checkpoint(cls, date: str) -> "PipelineState | None":
        """读 checkpoint，文件不存在或损坏时返回 None。"""
        checkpoint_path = CHECKPOINT_DIR / f"{date}.json"
        if not checkpoint_path.exists():
            return None
        try:
            data = json.loads(checkpoint_path.read_text())
            state = cls(
                run_id=data["run_id"],
                date=data["date"],
                status=data.get("status", "running"),
                current_engine=data.get("current_engine", ""),
            )
            state.completed_engines = [
                EngineResult(**e) for e in data.get("completed_engines", [])
            ]
            return state
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def mark_engine_done(
        self,
        engine: str,
        status: str,
        output_file: str = "",
        error: str = "",
        metrics: dict = None,
    ):
        """标记一个 engine 完成并自动写 checkpoint。"""
        result = EngineResult(
            engine=engine,
            status=status,
            started_at=self.current_engine_started_at
            if hasattr(self, "current_engine_started_at")
            else datetime.now().isoformat(),
            finished_at=datetime.now().isoformat(),
            output_file=output_file,
            error=error,
            metrics=metrics or {},
        )
        self.completed_engines.append(result)
        self.current_engine = ""

        # 检查是否全部完成
        done_names = {e.engine for e in self._engine_results()}
        if all(eng in done_names for eng in ENGINE_ORDER):
            has_failure = any(
                e.status == "failed" for e in self._engine_results()
            )
            self.status = "failed" if has_failure else "completed"

        self.save_checkpoint()

    def get_next_engine(self) -> "str | None":
        """返回下一个待执行的 engine 名，全部完成则返回 None。"""
        done_names = {e.engine for e in self._engine_results()}
        for engine in ENGINE_ORDER:
            if engine not in done_names:
                return engine
        return None

    def is_engine_done(self, engine: str) -> bool:
        """检查某个 engine 是否已完成（success 或 skipped）。"""
        return any(
            e.engine == engine and e.status in ("success", "skipped")
            for e in self._engine_results()
        )

    def start_engine(self, engine: str):
        """记录当前正在执行的 engine。"""
        self.current_engine = engine
        self.current_engine_started_at = datetime.now().isoformat()
        self.save_checkpoint()

    def _engine_results(self) -> "list[EngineResult]":
        """返回 completed_engines 列表，兼容 dict 和 EngineResult。"""
        results = []
        for e in self.completed_engines:
            if isinstance(e, EngineResult):
                results.append(e)
            elif isinstance(e, dict):
                results.append(EngineResult(**e))
        return results
