#!/bin/bash


declare -a PUBLICATIONS_COUNTS=(10000 20000 50000)
declare -a SUBSCRIPTIONS_COUNTS=(10000 20000 50000)
declare -a PROCESSES_COUNTS=(2 4 8 16)
declare -a THREADS_COUNTS=(1 2 4)


RESULTS_FILE="results.csv"
echo "Publications,Subscriptions,Processes,Threads,Execution Time" > $RESULTS_FILE


for PUB_COUNT in "${PUBLICATIONS_COUNTS[@]}"; do
    for SUB_COUNT in "${SUBSCRIPTIONS_COUNTS[@]}"; do
        for PROC_COUNT in "${PROCESSES_COUNTS[@]}"; do
            for THREAD_COUNT in "${THREADS_COUNTS[@]}"; do
                echo "Running test: Publications=$PUB_COUNT, Subscriptions=$SUB_COUNT, Processes=$PROC_COUNT, Threads=$THREAD_COUNT"
                
             
                export PUBLICATIONS_COUNT=$PUB_COUNT
                export SUBSCRIPTIONS_COUNT=$SUB_COUNT
                export PROCESSES=$PROC_COUNT
                export THREADS=$THREAD_COUNT
                
                
                START_TIME=$(date +%s.%N)
                python3 main.py
                END_TIME=$(date +%s.%N)
                EXECUTION_TIME=$(awk "BEGIN {print $END_TIME - $START_TIME}")
                
                echo "$PUB_COUNT,$SUB_COUNT,$PROC_COUNT,$THREAD_COUNT,$EXECUTION_TIME" >> $RESULTS_FILE
            done
        done
    done
done

echo "Tests completed. Results saved in $RESULTS_FILE."
