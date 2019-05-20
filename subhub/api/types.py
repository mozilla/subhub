from typing import Any, Dict, List, Tuple

# API types
JsonDict = Dict[str, Any]
FlaskResponse = Tuple[JsonDict, int]
FlaskListResponse = Tuple[List[JsonDict], int]
