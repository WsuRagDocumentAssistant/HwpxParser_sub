#================================================
# hwpx/__init__.py
#
# analysis / parser / document 를 하나로 묶는 이름공간.
#
# 자주 쓰는 둘만 여기로 올린다. 문서를 결과 객체로 만드는 데 필요한 것이
# 이 둘뿐이라, 쓰는 쪽이 하위 경로를 몰라도 된다.
#
#     import hwpx
#     parser, result = hwpx.run_pipeline('문서.hwpx', out_root='작업폴더')
#     model = hwpx.build_document_model(result)
#
# 나머지는 하위 모듈에서 직접 가져온다.
#     from hwpx.analysis.table_filter import apply_filter_to_state
#================================================

from .analysis.build_document_model import build_document_model
from .runner import run_pipeline

__all__ = ['run_pipeline', 'build_document_model']
