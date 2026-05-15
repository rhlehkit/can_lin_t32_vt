# CAPL Bridge Implementation Guide

이 문서는 `canoe_test_unit/bus_framework/bus_bridge_contract.can`의 stub 함수를 실제 프로젝트에 맞게 구현할 때 참고하는 가이드입니다.

## 설계 원칙

Python Test Unit은 테스트 시나리오와 판정만 담당합니다.

CAPL bridge는 아래 일을 담당합니다.

- CAN/LIN frame 송신
- CAN/LIN frame 수신 event 처리
- RX queue 저장
- 주기 송신 timer
- 수신 주기 측정
- timeout 처리
- 마지막 RX frame과 period 통계 제공

## 반환값 규칙

모든 exported function은 아래 규칙을 따릅니다.

| Return | 의미 |
| --- | --- |
| `0` | 성공 |
| `0 이외` | 실패 |

실패 시 `gLastError`에 상세 코드를 저장하고, Python은 `BusBridge_GetLastError()`로 읽습니다.

권장 error code:

| Code | 의미 |
| --- | --- |
| `0` | OK |
| `1001` | timeout |
| `1002` | invalid channel |
| `1003` | invalid DLC |
| `1004` | queue overflow |
| `1005` | period out of tolerance |
| `9001` | not implemented |

## CAN RX Queue 권장 구조

CAN RX는 Python polling으로 받지 말고 CAPL event에서 즉시 저장합니다.

권장 데이터:

```text
rxQueue[N]
  channel
  id
  extended
  dlc
  data0..data7
  timestampUs

rxWriteIndex
rxReadIndex
rxOverflowCounter
```

동작:

```text
on every received CAN frame:
  if queue full:
    overflow++
  else:
    copy channel/id/dlc/data/timestamp to rxQueue[write % N]
    write++
```

`BusBridge_WaitCan()`:

```text
deadline = now + timeout
while now < deadline:
  scan unread queue entries
  if channel/id/extended matches:
    copy entry to gLastRx*
    advance read pointer or mark entry consumed
    return 0
return timeout error
```

## LIN RX Queue 권장 구조

LIN도 같은 구조를 권장합니다.

```text
linRxQueue[N]
  channel
  frameId
  dlc
  data0..data7
  checksumStatus
  timestampUs
```

LIN은 프로젝트별로 다음 차이가 큽니다.

- master가 header를 보낼지
- DUT가 slave response를 낼지
- CANoe가 slave simulation을 할지
- LDF schedule table이 이미 frame 주기를 만들고 있는지
- classic/enhanced checksum 구성이 무엇인지

따라서 `BusBridge_RequestLinHeader()`와 `BusBridge_SendLin()`은 프로젝트 역할에 맞게 나누어 구현합니다.

## 주기 송신 구현

`BusBridge_StartCanPeriodic()` / `BusBridge_StartLinPeriodic()`은 `taskId`별 timer를 관리합니다.

권장 데이터:

```text
periodicTask[taskId]
  enabled
  busType
  channel
  id
  extended
  dlc
  data0..data7
  periodMs
```

동작:

```text
StartPeriodic:
  validate taskId and dlc
  store config
  set enabled = 1
  set timer(periodMs)

on timer:
  if enabled:
    output CAN frame or LIN header/frame
    set timer(periodMs)

StopPeriodic:
  set enabled = 0
  cancel timer
```

## 주기 체크 구현

`BusBridge_CheckCanPeriod()` / `BusBridge_CheckLinPeriod()`은 수신 frame timestamp로 interval을 계산합니다.

동작:

```text
lastTimestamp = invalid
sampleCount = 0
min = large
max = 0
sum = 0
deadline = now + timeout

while sampleCount < requestedSamples and now < deadline:
  wait matching frame
  if lastTimestamp valid:
    delta = timestamp - lastTimestamp
    if abs(delta - expectedPeriod) > tolerance:
      save stats
      return period error
    update min/max/sum
    sampleCount++
  lastTimestamp = timestamp

if sampleCount < requestedSamples:
  return timeout

save avg/min/max/sampleCount
return 0
```

단위는 Python 쪽과 맞추기 위해 `BusBridge_GetPeriod*()`에서 microsecond를 반환하는 것을 권장합니다.

## Python과 맞춰야 하는 함수

Python이 호출하는 함수 이름과 인자는 `bus_test_lib.py`에 고정되어 있습니다. CAPL 쪽에서 이름을 바꾸면 Python adapter도 같이 바꿔야 합니다.

가장 먼저 구현할 순서는 다음이 좋습니다.

1. `BusBridge_SendCan`
2. `BusBridge_WaitCan`
3. `BusBridge_CheckCanPeriod`
4. `BusBridge_StartCanPeriodic` / `BusBridge_StopPeriodic`
5. `BusBridge_RequestLinHeader`
6. `BusBridge_WaitLin`
7. `BusBridge_CheckLinPeriod`
8. `BusBridge_SendLin`
9. `BusBridge_StartLinPeriodic`

