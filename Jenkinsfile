pipeline {
    agent any
    
    parameters {
        string(name: 'QEMU_IMAGE_PATH', defaultValue: 'romulus/obmc-phosphor-image-romulus-20250916112422.static.mtd', description: 'Путь к образу OpenBMC')
        string(name: 'BMC_IP', defaultValue: 'localhost', description: 'IP адрес BMC')
        string(name: 'SSH_PORT', defaultValue: '2222', description: 'SSH порт')
        string(name: 'HTTPS_PORT', defaultValue: '2443', description: 'HTTPS порт')
        string(name: 'IPMI_PORT', defaultValue: '2623', description: 'IPMI порт')
    }
    
    environment {
        QEMU_PID_FILE = 'qemu.pid'
        QEMU_LOG_FILE = 'qemu.log'
        TEST_RESULTS_DIR = 'test-results'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Подготовка окружения') {
            steps {
                echo '=== Подготовка тестового окружения ==='
                sh '''
                    set +x
                    if ! command -v qemu-system-arm >/dev/null 2>&1; then
                    echo "ОШИБКА: qemu-system-arm не установлен в контейнере Jenkins"
                    exit 1
                    fi

                    mkdir -p ${TEST_RESULTS_DIR}

                    if [ ! -f ${QEMU_IMAGE_PATH} ]; then
                        echo "ОШИБКА: Образ OpenBMC не найден по пути ${QEMU_IMAGE_PATH}"
                        exit 1
                    fi

                    echo "Образ OpenBMC найден: ${QEMU_IMAGE_PATH}"

                    command -v qemu-system-arm >/dev/null 2>&1 || { echo "ОШИБКА: qemu-system-arm не установлен"; exit 1; }
                    command -v curl >/dev/null 2>&1 || { echo "ОШИБКА: curl не установлен"; exit 1; }
                '''
            }
        }
        
        stage('Запуск QEMU с OpenBMC') {
            steps {
                echo '=== Запуск QEMU эмулятора с OpenBMC ==='
                sh '''
                    set +x
                    if [ -f ${QEMU_PID_FILE} ]; then
                        OLD_PID=$(cat ${QEMU_PID_FILE})
                        if ps -p $OLD_PID > /dev/null 2>&1; then
                            echo "Остановка старого процесса QEMU (PID: $OLD_PID)"
                            kill -9 $OLD_PID || true
                        fi
                        rm -f ${QEMU_PID_FILE}
                    fi
                    
                    nohup qemu-system-arm -m 256 -M romulus-bmc -nographic -drive file=${QEMU_IMAGE_PATH},format=raw,if=mtd -net nic \\
                        -net user,hostfwd=tcp::${SSH_PORT}-:22,hostfwd=tcp::${HTTPS_PORT}-:443,hostfwd=tcp::${IPMI_PORT}-:623,hostname=qemu > ${QEMU_LOG_FILE} 2>&1 &

                    echo $! > ${QEMU_PID_FILE}
                    QEMU_PID=$(cat ${QEMU_PID_FILE})
                    
                    echo "QEMU запущен с PID: $QEMU_PID"
                    echo "Логи записываются в: ${QEMU_LOG_FILE}"
                    sleep 120
                '''
            }
        }
        
        stage('Автотесты OpenBMC (API)') {
            steps {
                echo '=== Запуск автоматических тестов API OpenBMC ==='
                sh '''
                    #!/bin/bash
                    set +x
                    
                    REPORT_FILE="${TEST_RESULTS_DIR}/api_test_report.txt"
                    REPORT_JSON="${TEST_RESULTS_DIR}/api_test_report.json"
                    
                    echo "!Отчет по тестированию API OpenBMC!" > $REPORT_FILE
                    echo "Дата: $(date)" >> $REPORT_FILE
                    echo "BMC Target: ${BMC_IP}:${HTTPS_PORT}" >> $REPORT_FILE
                    echo "" >> $REPORT_FILE

                    echo '{"test_suite": "API Tests", "timestamp": "'$(date -Iseconds)'", "tests": [' > $REPORT_JSON
                    
                    PASSED=0
                    FAILED=0

                    run_test() {
                        local test_name="$1"
                        local test_cmd="$2"
                        local expected_code="$3"
                        
                        echo "Тест: $test_name" >> $REPORT_FILE
                        
                        HTTP_CODE=$(eval "$test_cmd" 2>/dev/null || echo "000")
                        
                        if echo "$HTTP_CODE" | grep -q "$expected_code"; then
                            echo "  Результат: PASSED (HTTP $HTTP_CODE)" >> $REPORT_FILE
                            PASSED=$((PASSED + 1))
                            echo '{"name": "'$test_name'", "status": "PASSED", "http_code": "'$HTTP_CODE'"},' >> $REPORT_JSON
                        else
                            echo "  Результат: FAILED (HTTP $HTTP_CODE, ожидался $expected_code)" >> $REPORT_FILE
                            FAILED=$((FAILED + 1))
                            echo '{"name": "'$test_name'", "status": "FAILED", "http_code": "'$HTTP_CODE'", "expected": "'$expected_code'"},' >> $REPORT_JSON
                        fi
                        echo "" >> $REPORT_FILE
                    }
                    
                    # Тест 1: Проверка доступности Redfish Service Root
                    run_test "Redfish Service Root" "curl -k -s -o /dev/null -w '%{http_code}' https://${BMC_IP}:${HTTPS_PORT}/redfish/v1" "200\\|401"
                    
                    # Тест 2: Проверка SessionService
                    run_test "Redfish Session Service" "curl -k -s -o /dev/null -w '%{http_code}' https://${BMC_IP}:${HTTPS_PORT}/redfish/v1/SessionService" "200\\|401"
                    
                    # Тест 3: Проверка Systems
                    run_test "Redfish Systems Collection" "curl -k -s -o /dev/null -w '%{http_code}' https://${BMC_IP}:${HTTPS_PORT}/redfish/v1/Systems" "200\\|401"
                    
                    # Тест 4: Проверка Chassis
                    run_test "Redfish Chassis Collection" "curl -k -s -o /dev/null -w '%{http_code}' https://${BMC_IP}:${HTTPS_PORT}/redfish/v1/Chassis" "200\\|401"
                    
                    # Тест 5: Проверка Managers
                    run_test "Redfish Managers Collection" "curl -k -s -o /dev/null -w '%{http_code}' https://${BMC_IP}:${HTTPS_PORT}/redfish/v1/Managers" "200\\|401"

                    sed -i '$ s/,$//' $REPORT_JSON
                    echo '], "summary": {"total": '$((PASSED + FAILED))', "passed": '$PASSED', "failed": '$FAILED'}}' >> $REPORT_JSON

                    echo "ИТОГО:" >> $REPORT_FILE
                    echo "  Пройдено: $PASSED" >> $REPORT_FILE
                    echo "  Провалено: $FAILED" >> $REPORT_FILE
                    echo "  Всего: $((PASSED + FAILED))" >> $REPORT_FILE
                    
                    cat $REPORT_FILE
                '''
            }
        }
        
        stage('WebUI тесты OpenBMC') {
            steps {
                echo '=== Запуск тестов веб-интерфейса OpenBMC ==='
                sh '''
                    #!/bin/bash
                    set +x

                    REPORT_FILE="${TEST_RESULTS_DIR}/webui_test_report.txt"
                    REPORT_JSON="${TEST_RESULTS_DIR}/webui_test_report.json"
                    
                    echo "!Отчет по тестированию WebUI OpenBMC!" > $REPORT_FILE
                    echo "Дата: $(date)" >> $REPORT_FILE
                    echo "BMC Target: ${BMC_IP}:${HTTPS_PORT}" >> $REPORT_FILE
                    echo "" >> $REPORT_FILE
                    
                    echo '{"test_suite": "WebUI Tests", "timestamp": "'$(date -Iseconds)'", "tests": [' > $REPORT_JSON
                    
                    PASSED=0
                    FAILED=0

                    test_webpage() {
                        local test_name="$1"
                        local url="$2"
                        local expected_content="$3"

                        echo "Тест: $test_name" >> $REPORT_FILE
                        
                        RESPONSE=$(curl -k -s -w "\\nHTTP_CODE:%{http_code}" "$url" 2>/dev/null || echo "ERROR")
                        HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
                        CONTENT=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")
                        
                        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "302" ]; then
                            if [ -n "$expected_content" ] && echo "$CONTENT" | grep -qi "$expected_content"; then
                                echo "  Результат: PASSED (HTTP $HTTP_CODE, найден контент: $expected_content)" >> $REPORT_FILE
                                PASSED=$((PASSED + 1))
                                echo '{"name": "'$test_name'", "status": "PASSED", "http_code": "'$HTTP_CODE'"},' >> $REPORT_JSON
                            elif [ -z "$expected_content" ]; then
                                echo "  Результат: PASSED (HTTP $HTTP_CODE)" >> $REPORT_FILE
                                PASSED=$((PASSED + 1))
                                echo '{"name": "'$test_name'", "status": "PASSED", "http_code": "'$HTTP_CODE'"},' >> $REPORT_JSON
                            else
                                echo "  Результат: FAILED (контент не найден)" >> $REPORT_FILE
                                FAILED=$((FAILED + 1))
                                echo '{"name": "'$test_name'", "status": "FAILED", "reason": "content not found"},' >> $REPORT_JSON
                            fi
                        else
                            echo "  Результат: FAILED (HTTP $HTTP_CODE)" >> $REPORT_FILE
                            FAILED=$((FAILED + 1))
                            echo '{"name": "'$test_name'", "status": "FAILED", "http_code": "'$HTTP_CODE'"},' >> $REPORT_JSON
                        fi
                        echo "" >> $REPORT_FILE
                    }

                    # Тест 1: Главная страница
                    test_webpage "Главная страница WebUI" "https://${BMC_IP}:${HTTPS_PORT}/" ""
                    
                    # Тест 2: Страница входа
                    test_webpage "Страница входа" "https://${BMC_IP}:${HTTPS_PORT}/login" ""
                    
                    # Тест 3: Redfish веб-интерфейс
                    test_webpage "Redfish интерфейс" "https://${BMC_IP}:${HTTPS_PORT}/redfish/v1" "redfish\\|RedfishVersion"
                    
                    # Тест 4: Проверка статических ресурсов
                    test_webpage "Статические ресурсы CSS" "https://${BMC_IP}:${HTTPS_PORT}/assets/styles.css" ""
                    
                    # Тест 5: API документация
                    test_webpage "API документация" "https://${BMC_IP}:${HTTPS_PORT}/redfish/v1/\\$metadata" ""

                    sed -i '$ s/,$//' $REPORT_JSON
                    echo '], "summary": {"total": '$((PASSED + FAILED))', "passed": '$PASSED', "failed": '$FAILED'}}' >> $REPORT_JSON

                    echo "ИТОГО:" >> $REPORT_FILE
                    echo "  Пройдено: $PASSED" >> $REPORT_FILE
                    echo "  Провалено: $FAILED" >> $REPORT_FILE
                    echo "  Всего: $((PASSED + FAILED))" >> $REPORT_FILE
                    
                    cat $REPORT_FILE
                '''
            }
        }
        
        stage('Нагрузочное тестирование OpenBMC') {
            steps {
                echo '=== Запуск нагрузочного тестирования OpenBMC ==='
                sh '''
                    set +x
                    bash <<'EOF'
                    REPORT_FILE="${TEST_RESULTS_DIR}/load_test_report.txt"
                    REPORT_JSON="${TEST_RESULTS_DIR}/load_test_report.json"

                    echo "!Отчет по нагрузочному тестированию OpenBMC!" > $REPORT_FILE
                    echo "Дата: $(date)" >> $REPORT_FILE
                    echo "BMC Target: ${BMC_IP}:${HTTPS_PORT}" >> $REPORT_FILE
                    echo "" >> $REPORT_FILE

                    echo '{"test_suite": "Load Tests", "timestamp": "'$(date -Iseconds)'", "tests": [' > $REPORT_JSON

                    # Тест 1: Последовательные запросы
                    echo "--- Тест 1: Последовательные запросы ---" >> $REPORT_FILE
                    ITERATIONS=50
                    SUCCESS=0
                    FAILED_REQUESTS=0
                    TOTAL_TIME=0

                    for i in $(seq 1 $ITERATIONS); do
                        START=$(date +%s%N)
                        HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" https://${BMC_IP}:${HTTPS_PORT}/redfish/v1 2>/dev/null || echo "000")
                        END=$(date +%s%N)
                        DURATION=$((($END - $START) / 1000000))
                        TOTAL_TIME=$(($TOTAL_TIME + $DURATION))
                        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
                            SUCCESS=$(($SUCCESS + 1))
                        else
                            FAILED_REQUESTS=$(($FAILED_REQUESTS + 1))
                        fi
                        if [ $(($i % 10)) -eq 0 ]; then
                            echo "  Прогресс: $i/$ITERATIONS запросов выполнено" >> $REPORT_FILE
                        fi
                    done
                    AVG_TIME=$(($TOTAL_TIME / $ITERATIONS))
                    echo "" >> $REPORT_FILE
                    echo "Результаты последовательных запросов:" >> $REPORT_FILE
                    echo "  Всего запросов: $ITERATIONS" >> $REPORT_FILE
                    echo "  Успешных: $SUCCESS" >> $REPORT_FILE
                    echo "  Неудачных: $FAILED_REQUESTS" >> $REPORT_FILE
                    echo "  Среднее время ответа: ${AVG_TIME}ms" >> $REPORT_FILE
                    echo "" >> $REPORT_FILE
                    echo '{"name": "Sequential Requests", "total": '$ITERATIONS', "success": '$SUCCESS', "failed": '$FAILED_REQUESTS', "avg_response_time_ms": '$AVG_TIME'},' >> $REPORT_JSON

                    # Тест 2: Параллельные запросы
                    echo "--- Тест 2: Параллельные запросы ---" >> $REPORT_FILE
                    PARALLEL_REQUESTS=10
                    START_PARALLEL=$(date +%s%N)
                    for i in $(seq 1 $PARALLEL_REQUESTS); do
                        (
                            HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" https://${BMC_IP}:${HTTPS_PORT}/redfish/v1 2>/dev/null || echo "000")
                            if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
                                echo "SUCCESS" >> $REPORT_FILE
                            fi
                        ) >/dev/null 2>&1 &
                    done
                    wait
                    END_PARALLEL=$(date +%s%N)
                    PARALLEL_DURATION=$((($END_PARALLEL - $START_PARALLEL) / 1000000))
                    echo "" >> $REPORT_FILE
                    echo "Результаты параллельных запросов:" >> $REPORT_FILE
                    echo "  Количество запросов: $PARALLEL_REQUESTS" >> $REPORT_FILE
                    echo "  Общее время выполнения: ${PARALLEL_DURATION}ms" >> $REPORT_FILE
                    echo "" >> $REPORT_FILE
                    echo '{"name": "Parallel Requests", "concurrent": '$PARALLEL_REQUESTS', "total_time_ms": '$PARALLEL_DURATION'},' >> $REPORT_JSON

                    # Тест 3: Стресс-тест (множественные эндпоинты)
                    echo "--- Тест 3: Стресс-тест различных эндпоинтов ---" >> $REPORT_FILE
                    ENDPOINTS=("/redfish/v1" "/redfish/v1/Systems" "/redfish/v1/Chassis" "/redfish/v1/Managers" "/redfish/v1/SessionService")
                    STRESS_SUCCESS=0
                    STRESS_FAILED=0
                    for endpoint in "${ENDPOINTS[@]}"; do
                        for i in $(seq 1 10); do
                            HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" "https://${BMC_IP}:${HTTPS_PORT}${endpoint}" 2>/dev/null || echo "000")
                            if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
                                STRESS_SUCCESS=$(($STRESS_SUCCESS + 1))
                            else
                                STRESS_FAILED=$(($STRESS_FAILED + 1))
                            fi
                        done
                    done
                    echo "Результаты стресс-теста:" >> $REPORT_FILE
                    echo "  Успешных запросов: $STRESS_SUCCESS" >> $REPORT_FILE
                    echo "  Неудачных запросов: $STRESS_FAILED" >> $REPORT_FILE
                    echo "" >> $REPORT_FILE
                    echo '{"name": "Stress Test", "success": '$STRESS_SUCCESS', "failed": '$STRESS_FAILED'}' >> $REPORT_JSON

                    echo '], "summary": {"sequential_avg_ms": '$AVG_TIME', "parallel_time_ms": '$PARALLEL_DURATION', "stress_success": '$STRESS_SUCCESS', "stress_failed": '$STRESS_FAILED'}}' >> $REPORT_JSON
                    echo "ИТОГО:" >> $REPORT_FILE
                    echo "  Среднее время последовательных запросов: ${AVG_TIME}ms" >> $REPORT_FILE
                    echo "  Общее время параллельных запросов: ${PARALLEL_DURATION}ms" >> $REPORT_FILE
                    echo "  Стресс-тест - успешно: $STRESS_SUCCESS, провалено: $STRESS_FAILED" >> $REPORT_FILE
                    cat $REPORT_FILE
EOF
        '''
            }
        }
    }
    
    post {
        always {
            echo '=== Завершение работы и очистка ==='
            archiveArtifacts artifacts: 'test-results/**/*.txt, test-results/**/*.json, qemu.log', allowEmptyArchive: true, fingerprint: true
            sh '''
                set +x
                if [ -f ${QEMU_PID_FILE} ]; then
                    PID=$(cat ${QEMU_PID_FILE})
                    if ps -p $PID > /dev/null 2>&1; then
                        echo "Остановка QEMU процесса (PID: $PID)"
                        kill $PID 2>/dev/null || true
                        sleep 2

                        if ps -p $PID > /dev/null 2>&1; then
                            echo "Принудительная остановка QEMU"
                            kill -9 $PID 2>/dev/null || true
                        fi
                        
                        echo "QEMU успешно остановлен"
                    else
                        echo "Процесс QEMU уже остановлен"
                    fi
                    
                    rm -f ${QEMU_PID_FILE}
                else
                    echo "PID файл QEMU не найден"
                fi
            '''
        }
        
        success {
            echo 'Pipeline успешно завершен'
        }
        
        failure {
            echo 'Pipeline завершился с ошибками'
        }
        
        unstable {
            echo 'Pipeline завершен с предупреждениями'
        }
    }
}
