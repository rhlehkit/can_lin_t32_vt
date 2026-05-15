# CANoe/vTESTstudio Python Runtime Package Install Guide

이 문서는 CANoe/vTESTstudio Test Unit에서 사용하는 Python runtime에 외부 package를 설치하는 방법입니다.

TRACE32 연동 예제에서는 아래 package가 필요합니다.

```powershell
lauterbach-trace32-rcl~=1.1.0
```

## 핵심 결론

가장 확실한 방법은 **Test Unit이 실제로 사용하는 `python.exe`를 먼저 확인한 뒤, 그 `python.exe -m pip install ...`로 설치하는 것**입니다.

이를 위해 `bus_framework`에 진단 TC를 추가했습니다.

```text
TC_PYTHON_RuntimeInfo
```

이 TC를 실행하면 Test Report에 다음 정보가 찍힙니다.

- `sys.executable`
- Python version
- `sys.prefix`
- site-packages 경로
- `sys.path`

## 1. 공식 문서에서 확인한 내용

Vector Simulation and Test Environment VS Code extension 문서 기준:

- Python simulation node/application model 편집 시 `.vector` 디렉터리에 virtual Python environment가 생성됩니다.
- VS Code Python extension이 이 환경을 로드하도록 제안합니다.
- Vector toolset이 요구하는 Python version이 설치되어 있어야 합니다.
- 시스템 Python을 바꾼 뒤에는 `Recreate virtual Python environment` 명령으로 가상환경을 다시 만들 수 있습니다.

Vector Test Unit VS Code extension 문서 기준:

- Python/CAPL/C# test implementation을 지원합니다.
- Python test file은 Vector type library와 CAPL library symbol을 사용할 수 있게 확장이 도와줍니다.
- Python package resolution은 Pylance가 처리합니다.
- 실제 CANoe GUI workflow에서 test compile/run은 CANoe Test Configuration에서 수행합니다.

즉, 편집용 Python 환경과 실제 실행 runtime이 다를 수 있으므로 `TC_PYTHON_RuntimeInfo`로 실제 실행 runtime을 확인하는 게 안전합니다.

## 2. CANoe GUI Test Unit workflow에서 설치

CANoe Test Configuration에서 `bus_framework.vtestunit.yaml`을 추가한 뒤:

1. `TC_PYTHON_RuntimeInfo`를 실행합니다.
2. Test Report에서 `Python executable` 값을 확인합니다.
3. 해당 경로를 복사합니다.
4. PowerShell에서 아래처럼 설치합니다.

```powershell
"&C:\Path\To\Python\python.exe" -m pip install "lauterbach-trace32-rcl~=1.1.0"
```

예:

```powershell
&"C:\Users\me\AppData\Local\Programs\Python\Python39\python.exe" -m pip install "lauterbach-trace32-rcl~=1.1.0"
```

설치 확인:

```powershell
&"C:\Path\To\Python\python.exe" -c "import lauterbach.trace32.rcl as t32; print('ok')"
```

## 3. `.vector` virtual environment에 설치

DevOps/Server Edition workflow 또는 Vector Simulation and Test Environment를 쓰는 경우 `.vector` 아래 virtual environment가 생성될 수 있습니다.

프로젝트 루트에서 Python exe를 찾습니다.

```powershell
Get-ChildItem .vector -Recurse -Filter python.exe |
  Where-Object { $_.FullName -match "\\Scripts\\python.exe$" } |
  Select-Object FullName
```

찾은 경로에 설치합니다.

```powershell
&".vector\...\Scripts\python.exe" -m pip install "lauterbach-trace32-rcl~=1.1.0"
```

Python 설치나 Vector toolset 변경 후 environment가 꼬이면 VS Code Command Palette에서 아래 명령을 실행합니다.

```text
Recreate virtual Python environment
```

그 다음 package를 다시 설치합니다.

## 4. pip가 없는 경우

해당 Python에 pip가 없으면 먼저 확인합니다.

```powershell
&"C:\Path\To\Python\python.exe" -m pip --version
```

실패하면:

```powershell
&"C:\Path\To\Python\python.exe" -m ensurepip --upgrade
&"C:\Path\To\Python\python.exe" -m pip install --upgrade pip
```

회사 PC 정책상 `ensurepip` 또는 인터넷 설치가 막혀 있으면, wheel 파일을 받아서 local install 해야 합니다.

## 5. 인터넷이 막힌 PC에서 설치

인터넷 가능한 PC에서 wheel을 다운로드합니다.

```powershell
py -m pip download "lauterbach-trace32-rcl~=1.1.0" -d .\wheels
```

대상 PC로 `wheels` 폴더를 복사한 뒤:

```powershell
&"C:\Path\To\Python\python.exe" -m pip install --no-index --find-links .\wheels "lauterbach-trace32-rcl~=1.1.0"
```

TRACE32 설치 폴더에도 wheel이 있을 수 있습니다.

```text
<T32SYS>\demo\api\python\rcl\dist
```

## 6. 이 프로젝트에 적용된 내용

`pyproject.toml`에는 optional dependency를 추가했습니다.

```toml
[project.optional-dependencies]
trace32 = ["lauterbach-trace32-rcl~=1.1.0"]
```

프로젝트를 editable install로 쓸 수 있는 환경이면 아래도 가능합니다.

```powershell
&"C:\Path\To\Python\python.exe" -m pip install -e ".[trace32]"
```

다만 CANoe/vTESTstudio 환경에서는 보통 필요한 package만 직접 설치하는 방식이 더 단순합니다.

## 7. 설치 후 확인 순서

1. `TC_PYTHON_RuntimeInfo` 실행
2. `Python executable` 확인
3. 해당 `python.exe`에 package 설치
4. `TC_TRACE32_ConnectAndSnapshot` 실행
5. TRACE32 연결과 변수 출력 확인

