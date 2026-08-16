#================================================
# tools/check_standalone.py
#
# hwpx 패키지만으로 동작하는지 확인한다.
#
# 왜 필요한가
#   배포하면 쓰는 쪽에는 hwpx 만 간다. tools 는 이 저장소의 개발 도구라
#   설치되지 않는다. 그런데 개발 중에는 저장소 루트에서 돌리기 때문에
#   tools 에 있는 무언가에 기대고 있어도 티가 안 난다.
#
#   그래서 hwpx 만 빈 폴더에 복사해 그 안에서 돌린다. 저장소를 건드리지
#   않는다. 파일을 지워 확인할 필요가 없다.
#
# 사용:
#   python -m tools.check_standalone
#   python -m tools.check_standalone <문서>
#================================================

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from .defaults import DEFAULT_SOURCE, REPO_ROOT
except ImportError as exc:            # noqa: E402
    raise SystemExit(
        "이 파일은 모듈로 실행하세요.\n"
        "  python -m tools.check_standalone ..."
    ) from exc


# 격리 폴더 안에서 돌 코드. hwpx 외에는 아무것도 쓰지 않는다.
CONSUMER = '''
import io, contextlib, sys
sys.stdout.reconfigure(encoding="utf-8")
import hwpx
with contextlib.redirect_stdout(io.StringIO()):
    parser, result = hwpx.run_pipeline(sys.argv[1], sys.argv[2])
    model = hwpx.build_document_model(result)
print(f"블록 {len(model.blocks)} / 표 {len(list(model.tables()))} / 이미지 {len(model.images)}")
'''


def main(argv: list[str] | None = None) -> int:
    """
    역할: hwpx 만 복사한 폴더에서 문서 하나를 끝까지 돌려 본다.
    입력 데이터: argv(문서 경로).
    출력 데이터: 종료 코드.
    """
    from .audit.documents import enable_utf8_stdout
    enable_utf8_stdout()

    ap = argparse.ArgumentParser(description='hwpx 단독 동작 확인')
    ap.add_argument('source', nargs='?', default=str(DEFAULT_SOURCE))
    args = ap.parse_args(argv)

    source = Path(args.source)
    if not source.exists():
        print(f"[ERROR] 문서를 찾을 수 없습니다: {source}")
        return 1

    with tempfile.TemporaryDirectory(prefix='hwpx_standalone_') as tmp:
        room = Path(tmp)
        shutil.copytree(REPO_ROOT / 'hwpx', room / 'hwpx',
                        ignore=shutil.ignore_patterns('__pycache__'))
        script = room / 'consumer.py'
        script.write_text(CONSUMER, encoding='utf-8')

        print('===========================================')
        print('[hwpx 단독 동작 확인]')
        print(f'  격리 폴더 : {room}')
        print(f'  들어간 것 : hwpx 만 (tools 없음)')
        print(f'  문서      : {source}')
        print('-------------------------------------------')

        # PYTHONPATH 를 비워야 저장소 경로가 새어 들어가지 않는다. 그게 남아
        # 있으면 tools 가 보이는 채로 돌아 검사가 무력해진다.
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)

        done = subprocess.run(
            [sys.executable, str(script), str(source.resolve()), str(room / 'work')],
            cwd=room, capture_output=True, text=True, encoding='utf-8', env=env,
        )
        if done.stdout.strip():
            print(done.stdout.strip())
        if done.returncode != 0:
            # 마지막 몇 줄이 원인이다. 안 보여주면 무엇이 부족한지 알 수 없다.
            tail = [ln for ln in (done.stderr or '').splitlines() if ln.strip()]
            for line in tail[-6:]:
                print('  ' + line)
            print('===========================================')
            print('결과: FAIL - hwpx 만으로는 돌지 않습니다.')
            return 1

    print('===========================================')
    print('결과: PASS - hwpx 만으로 문서에서 모델까지 나옵니다.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
