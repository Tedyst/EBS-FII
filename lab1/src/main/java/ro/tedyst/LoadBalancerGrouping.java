package ro.tedyst;

import org.apache.storm.generated.GlobalStreamId;
import org.apache.storm.grouping.CustomStreamGrouping;
import org.apache.storm.task.WorkerTopologyContext;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class LoadBalancerGrouping implements CustomStreamGrouping {
    Map<Integer, Integer> load = new HashMap<>();

    public void prepare(WorkerTopologyContext context, GlobalStreamId stream, List<Integer> targetTasks) {
        for (int i = 0; i < targetTasks.size(); i++) {
            load.put(targetTasks.get(i), 0);
        }
    }
    public List<Integer> chooseTasks(int taskId, List<Object> values) {
        int taskDifficulty = (int) values.get(1);
        int minLoad = Integer.MAX_VALUE;
        int chosenTask = -1;
        for (Map.Entry<Integer, Integer> entry : load.entrySet()) {
            if (entry.getValue() < minLoad) {
                minLoad = entry.getValue();
                chosenTask = entry.getKey();
            }
        }
        load.put(chosenTask, load.get(chosenTask) + taskDifficulty);
        return List.of(chosenTask);
    }
}
