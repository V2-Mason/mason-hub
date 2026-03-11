"""
数据目录解析器 — 读取 data_catalog.yaml 并提供结构化查询。

支持四层架构查询：raw → clean → analysis → report
支持指标注册表查询。

维护者：EMP_0014
"""
import os
import yaml
from pathlib import Path

_CATALOG_PATH = Path(__file__).parent.parent / 'data_catalog.yaml'
_cache = None
_metrics_cache = None


def _load():
    """加载并缓存 data_catalog.yaml。"""
    global _cache, _metrics_cache
    if _cache is not None:
        return _cache
    with open(_CATALOG_PATH, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f)
    _cache = {ds['id']: ds for ds in raw.get('datasets', []) if ds.get('id')}
    _metrics_cache = {m['id']: m for m in raw.get('metrics', []) if m.get('id')}
    return _cache


def reload():
    """强制重新加载（catalog 文件更新后调用）。"""
    global _cache
    _cache = None
    return _load()


def get(dataset_id):
    """获取单个数据集元信息。

    Args:
        dataset_id: 数据集 ID（如 "raw_xhs_notes"）

    Returns:
        dict: 数据集定义，如不存在则 None
    """
    catalog = _load()
    return catalog.get(dataset_id)


def list_datasets(status=None, owner=None, layer=None):
    """列出数据集。

    Args:
        status: 过滤状态（"active", "planned", "stale", "deprecated"）
        owner: 过滤负责人
        layer: 过滤所属层（"raw", "clean", "analysis", "report"）

    Returns:
        list[dict]
    """
    catalog = _load()
    results = list(catalog.values())
    if status:
        results = [ds for ds in results if ds.get('status') == status]
    if owner:
        results = [ds for ds in results if ds.get('owner') == owner]
    if layer:
        results = [ds for ds in results if ds.get('layer') == layer]
    return results


def get_metric(metric_id):
    """获取指标定义。

    Args:
        metric_id: 指标 ID（如 "interaction_score"）

    Returns:
        dict: 指标定义，如不存在则 None
    """
    _load()
    return _metrics_cache.get(metric_id) if _metrics_cache else None


def list_metrics():
    """列出所有已注册指标。

    Returns:
        list[dict]
    """
    _load()
    return list(_metrics_cache.values()) if _metrics_cache else []


def get_layer_datasets(layer):
    """获取某一层的所有数据集。

    Args:
        layer: "raw" | "clean" | "analysis" | "report"

    Returns:
        list[dict]
    """
    return list_datasets(layer=layer)


def get_lineage(dataset_id):
    """获取数据集的数据血缘（上游 input 链路）。

    Args:
        dataset_id: 数据集 ID

    Returns:
        list[str]: 从当前数据集回溯到 raw 层的 ID 链
    """
    ds = get(dataset_id)
    if not ds:
        return []

    lineage = [dataset_id]
    inputs = ds.get('input', [])
    for inp in inputs:
        lineage.extend(get_lineage(inp))
    return lineage


def resolve_location(dataset_id):
    """解析数据集的物理存储路径。

    将 catalog 中的逻辑位置转换为本机可访问的路径：
    - gcp:~/xxx  →  展开 ~
    - aliyun:xxx →  查找 data/mirror/ 下的本地镜像
    - 直接路径  →  原样返回

    Returns:
        dict: {"type": str, "path": str, "table": str|None, "is_mirror": bool}
        如果数据集不存在返回 None
    """
    ds = get(dataset_id)
    if not ds:
        return None

    storage = ds.get('storage', {})
    stype = storage.get('type', 'unknown')
    location = storage.get('location', '')
    table = storage.get('table')

    hub_root = Path(__file__).parent.parent.parent  # mason-hub/
    mirror_root = hub_root / 'data' / 'mirror'

    is_mirror = False
    path = location

    if location.startswith('gcp:'):
        # gcp:~/mason-hub/xxx → expand to local path
        raw = location.replace('gcp:', '')
        path = str(Path(raw.replace('~/', str(Path.home()) + '/')))
        is_mirror = False
    elif location.startswith('aliyun:'):
        # aliyun:/opt/mediacrawler/... → look in data/mirror/
        remote_path = location.replace('aliyun:', '')
        # Map known aliyun paths to mirror structure
        if 'sqlite_tables.db' in remote_path:
            path = str(mirror_root / 'sqlite_tables.db')
            is_mirror = True
        elif '/analysis/trends/' in remote_path:
            path = str(mirror_root / 'analysis' / 'trends')
            is_mirror = True
        elif '/analysis/comments/' in remote_path:
            path = str(mirror_root / 'analysis' / 'comments')
            is_mirror = True
        elif '/analysis/briefings/' in remote_path or '/briefings/' in remote_path:
            path = str(mirror_root / 'briefings')
            is_mirror = True
        elif '/analysis/' in remote_path:
            path = str(mirror_root / 'analysis')
            is_mirror = True
        else:
            path = remote_path
            is_mirror = True

    return {
        'type': stype,
        'path': path,
        'table': table,
        'is_mirror': is_mirror,
        'dataset_id': dataset_id,
    }
