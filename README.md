# Vector CAN/LIN Python and CANoe/vTESTstudio Samples

이 저장소는 Vector 장비 기반 CAN/LIN 테스트 자동화를 위한 샘플 모음입니다.

두 가지 방향을 제공합니다.

1. Python에서 Vector XL Driver Library를 직접 호출해 VN16xx LIN을 제어하는 예제
2. CANoe/vTESTstudio Test Unit에서 Python TC를 실행하고 CAPL bridge를 통해 CAN/LIN TX, RX, 주기 송신, 주기 체크를 수행하는 예제
3. TRACE32 Remote API를 통해 ECU 내부 변수/레지스터 값을 읽어 Test Report에 남기는 예제

## 가장 중요한 폴더

```text
canoe_test_unit/bus_framework/
```

이 폴더가 CANoe/vTESTstudio에서 쓰기 위한 메인 프레임워크입니다.

제공 TC:

- `TC_EXAMPLE_CAN_SendAndExpectResponse`
- `TC_EXAMPLE_LIN_RequestAndExpectResponse`
- `TC_EXAMPLE_CAN_PeriodicWhileCheckingResponse`
- `TC_PYTHON_RuntimeInfo`
- `TC_TRACE32_ConnectAndSnapshot`
- `TC_TRACE32_AssertVariables`
- `TC_TRACE32_WriteVariables`
- `TC_CAN_TxThenTrace32Snapshot`
- `TC_CAN_RxThenTrace32Snapshot`
- `TC_TRACE32_WriteThenCanTx`
- `TC_LIN_RxThenTrace32Snapshot`
- `TC_CAN_TxOnce`
- `TC_CAN_RxExpect`
- `TC_CAN_PeriodicTx`
- `TC_CAN_PeriodicTx_Start`
- `TC_CAN_PeriodicTx_Stop`
- `TC_CAN_PeriodCheck`
- `TC_LIN_TxOnce`
- `TC_LIN_RxExpect`
- `TC_LIN_PeriodicTx`
- `TC_LIN_PeriodicTx_Start`
- `TC_LIN_PeriodicTx_Stop`
- `TC_LIN_PeriodCheck`

자세한 내용은 [bus_framework README](canoe_test_unit/bus_framework/README.md)를 보세요.

다른 PC 적용 절차는 [setup_on_another_pc.md](docs/setup_on_another_pc.md)에 정리했습니다.

## CANoe/vTESTstudio 권장 구조

Python이 VN 하드웨어를 직접 열지 않고, CANoe가 hardware/channel/database/LDF/VT System을 소유합니다.

```text
Python Test Case
  -> CAPL exported function
    -> CANoe CAN/LIN configuration
      -> Vector hardware / VT System / DUT
```

이 구조가 system variable만으로 프레임을 전달하는 방식보다 여러 RX frame, 주기 측정, overflow 처리에 유리합니다.

## 직접 XL Driver LIN 예제

`src/vector_lin`과 `examples`는 CANoe 없이 Python에서 XL Driver Library를 직접 호출하는 예제입니다.

예:

```powershell
python .\examples\lin_master_request.py --channel-index 0 --request-id 0x12 --count 10 --period-ms 100 --listen-ms 50
```

CANoe/vTESTstudio와 같은 VN channel을 동시에 잡으면 충돌할 수 있습니다. CANoe 기반 테스트에서는 `canoe_test_unit/bus_framework` 방식을 우선 사용하세요.

## 참고 문서

- [VT System / Python integration memo](docs/vt_system_python_integration.md)
- [Other PC setup guide](docs/setup_on_another_pc.md)
- [CAPL bridge implementation guide](docs/capl_bridge_implementation_guide.md)
- [How to add a simple TC](docs/how_to_add_simple_tc.md)
- [TRACE32 integration guide](docs/trace32_integration_guide.md)
- [Python runtime package install guide](docs/python_runtime_package_install_guide.md)
- [What is ready and what to customize](docs/what_is_ready_and_what_to_customize.md)
