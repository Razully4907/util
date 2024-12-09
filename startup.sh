#!/bin/bash

# 홈 폴더 설정
HOME_DIR=~
LOG_FILE="$HOME_DIR/startup.log"
PYTHON_SCRIPT_NAME="startup.py"
PYTHON_SCRIPT="$HOME_DIR/$PYTHON_SCRIPT_NAME"

# 로그 파일에서 마지막 timestamp 읽기
if [ ! -f "$LOG_FILE" ]; then
    echo "Warning: $LOG_FILE does not exist. Setting last_timestamp to 1."
    last_timestamp=1
else
    # 파일을 불러오지 못하면 기본값 1로 설정
    last_timestamp=$(tail -n 1 "$LOG_FILE" 2>/dev/null || echo 1)
fi

# 현재 시간 (초 단위로 가져오기)
current_timestamp=$(date +%s)

# 시간 차이 계산
time_difference=$((current_timestamp - last_timestamp))

# 15초 이상 차이나면 Python 스크립트 실행
if [ "$time_difference" -ge 15 ]; then

    # 실행 중인 프로세스를 찾아서 종료
    # echo "Finding and killing all processes running $PYTHON_SCRIPT_NAME..."

    # pgrep으로 해당 스크립트 프로세스 찾기
    pids=$(pgrep -f "$PYTHON_SCRIPT_NAME")

    # 프로세스를 종료
    # echo "Killing processes: $pids"
    kill $pids

    # echo "Timestamp difference is $time_difference seconds. Executing $PYTHON_SCRIPT..."
    nohup python3 "$PYTHON_SCRIPT" $
else
    # echo "Timestamp difference is only $time_difference seconds. No action taken."
fi
