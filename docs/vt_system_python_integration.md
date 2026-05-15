# Vector VT System / CANoe Python 연동 메모

## 핵심 결론

VT System은 Python 코드를 VT 하드웨어에 직접 넣어서 실행하는 방식이라기보다, CANoe 또는 vTESTstudio의 Test Unit 실행 환경에서 Python 테스트 케이스를 호출하고 그 테스트 케이스가 CANoe 측 리소스, 네트워크, 시스템 변수, VT System 채널을 제어하는 구조로 보는 것이 안전합니다.

따라서 이전에 만든 `vector_lin` 패키지를 그대로 VT System 안에 "설치"한다기보다는 아래 둘 중 하나로 접근하는 것이 좋습니다.

1. CANoe/vTESTstudio가 VN16xx LIN 채널과 VT System을 소유하게 두고, Python Test Unit에서 CANoe API를 통해 LIN/VT 동작을 수행한다.
2. CANoe가 해당 VN16xx LIN 채널을 사용하지 않는 상태에서만, Python Test Unit 또는 외부 프로세스가 `vector_lin`의 XL Driver 기반 코드를 호출한다.

1번이 VT System을 쓰는 정석 경로입니다. 2번은 빠른 실험에는 가능하지만 CANoe와 XL Driver 채널 점유가 충돌할 수 있습니다.

## 권장 구조

작업 폴더 예시는 다음처럼 둡니다.

```text
lin-vt-test/
  lin_vt_smoke.py
  lin_vt_smoke.vtestunit.yaml
  lin_vt_smoke.vtesttree.yaml
  vector_lin/                  # 필요 시 기존 패키지를 복사하거나 import path로 연결
```

`lin_vt_smoke.py`는 CANoe Python 테스트 케이스를 export하는 얇은 래퍼로 둡니다.

```python
import sys
from pathlib import Path

import vector.canoe
import vector.canoe.tfs


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def LinSmokeTest():
    # 권장: 여기서는 CANoe API / system variable / signal API를 통해 LIN과 VT를 제어합니다.
    # 주의: CANoe가 같은 VN16xx LIN 채널을 사용 중이면 vector_lin.VectorLinChannel로 직접 열지 않는 것이 좋습니다.
    vector.canoe.tfs.test_step("LIN smoke", "Python test case was called by CANoe/vTESTstudio.")
```

`lin_vt_smoke.vtestunit.yaml`은 Python 파일과 test tree를 Test Unit에 묶습니다.

```yaml
version: 1.0.0
test-unit: LinVtSmoke
test-unit-implementation:
  - source-file-path: lin_vt_smoke.py
  - source-file-path: lin_vt_smoke.vtesttree.yaml
```

`lin_vt_smoke.vtesttree.yaml`은 실행할 Python 테스트 케이스를 지정합니다.

```yaml
version: 1.0.0
test-tree:
  - python-test-case: LinSmokeTest
```

## CANoe / vTESTstudio에 넣는 흐름

1. Vector Test Unit VS Code 확장을 설치합니다.
2. CANoe 또는 vTESTstudio가 설치된 PC에서 위 파일들을 같은 테스트 폴더에 둡니다.
3. VS Code에서 `.vtestunit.yaml`을 열고 Python 테스트 파일 인식, export table 생성, type library 생성이 되는지 확인합니다.
4. CANoe Test Configuration 또는 vTESTstudio 프로젝트에 해당 Test Unit을 추가합니다.
5. CANoe 설정에서 VN16xx LIN 채널, LDF, VT System 구성을 먼저 정상 연결합니다.
6. Python 테스트 케이스 안에서는 가능하면 CANoe가 제공하는 API, system variables, signals, environment variables, VT System용 변수/서비스를 통해 장비를 제어합니다.

## 이전에 만든 `vector_lin` 코드를 넣을 때의 판단 기준

`vector_lin`은 Vector XL Driver Library를 직접 호출해서 VN16xx 채널을 여는 구조입니다. CANoe도 같은 드라이버와 같은 하드웨어 채널을 사용하므로, 둘이 동시에 같은 LIN 채널을 잡으려 하면 충돌할 수 있습니다.

그래서 VT System 기반 자동화에서는 다음처럼 나누는 편이 좋습니다.

| 목적 | 권장 방식 |
| --- | --- |
| CANoe 없이 VN16xx LIN을 Python에서 직접 제어 | `vector_lin.VectorLinChannel` 사용 |
| CANoe + VT System 테스트 자동화 | CANoe Python Test Unit 사용 |
| CANoe 실행 중 외부 Python 스크립트 호출 | CANoe가 해당 LIN 채널을 점유하지 않을 때만 제한적으로 사용 |
| 장기 유지보수용 테스트 | LIN 제어를 CANoe-native API/CAPL/Python Test Unit 쪽으로 이관 |

## 빠른 외부 호출 예시

아래 방식은 검증용입니다. CANoe가 같은 VN16xx LIN 채널을 잡고 있지 않을 때만 사용하세요.

```python
import subprocess
import sys
from pathlib import Path

import vector.canoe.tfs


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def RunExternalLinMasterRequest():
    repo = Path(__file__).resolve().parents[1]
    script = repo / "examples" / "lin_master_request.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--app-name",
            "python-lin",
            "--channel",
            "0",
            "--id",
            "0x12",
            "--data",
            "01 02 03 04",
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
```

## 실제 적용 전에 확인할 것

- 사용 중인 CANoe/vTESTstudio 버전이 Python Test Unit을 지원하는지 확인합니다.
- CANoe 설치 폴더의 Test Unit YAML schema를 확인합니다. 설치 버전에 따라 지원 키와 Python package path 지정 방식이 조금 다를 수 있습니다.
- VT System 채널명, system variable 이름, LIN database/LDF 이름은 프로젝트마다 다르므로 샘플 코드에서 직접 확정하기 어렵습니다.
- LIN 프레임 송수신 자체는 CANoe simulation/setup에 맡기고, Python에서는 테스트 시퀀스와 판정 로직을 담당하게 하는 구성이 가장 안정적입니다.

## LIN TX/RX 샘플

이 저장소에는 CANoe system variable을 bridge로 사용하는 샘플 Test Unit을 추가했습니다.

```text
canoe_test_unit/lin_rx_tx/
  lin_rx_tx_test.py
  lin_rx_tx.vtestunit.yaml
  lin_rx_tx.vtesttree.yaml
  README.md
```

이 샘플은 Python Test Unit에서 `LinTest::Tx*` system variable을 써서 LIN 송신을 요청하고, CANoe 쪽 bridge가 갱신한 `LinTest::Rx*` system variable을 읽어서 수신 프레임을 판정합니다.

## System variable을 쓰지 않는 대안

RX가 빠르게 여러 개 들어오거나 TX 요청을 연속으로 보내야 한다면 system variable만으로 프레임을 전달하는 방식은 금방 불편해집니다. 그 경우는 CAPL bridge를 두는 구조가 더 좋습니다.

```text
canoe_test_unit/lin_capl_bridge/
  lin_capl_bridge_test.py
  lin_bridge.can
  lin_capl_bridge.vtestunit.yaml
  lin_capl_bridge.vtesttree.yaml
  README.md
```

이 방식에서는 CAPL이 LIN 송수신, RX queue, timeout, LDF frame object 처리를 맡고 Python Test Unit은 CAPL exported function을 호출해서 테스트 판정만 수행합니다. Vector Test Unit 확장의 Python type library 생성 기능을 사용하면 CAPL exported function을 Python에서 더 자연스럽게 호출할 수 있습니다.

## CAN/LIN 공통 프레임워크

LIN뿐 아니라 CAN TX/RX, CAN 주기 송신, CAN 주기 체크까지 함께 다루기 위한 공통 Test Unit은 아래 폴더에 있습니다.

```text
canoe_test_unit/bus_framework/
```

이 프레임워크는 `bus_test_config.py`에서 ID, channel, data, period, tolerance만 바꾸고, `bus_bridge_contract.can`의 CAPL 함수 내부를 프로젝트 CANoe configuration에 맞게 구현하는 방식입니다.
