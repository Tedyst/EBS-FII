package ro.tedyst;

import java.util.Map;

import org.apache.storm.task.OutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichBolt;
import org.apache.storm.tuple.Fields;
import org.apache.storm.tuple.Tuple;
import org.apache.storm.tuple.Values;

public class SplitTextBolt extends BaseRichBolt {

    private static final long serialVersionUID = 2;

    private OutputCollector collector;
    private String task;
    private int task_id;
    private int processed_tuples = 0;

    // for custom grouping example
    private int drop_task;

    // remove template type qualifiers from conf declaration for Storm v1
    public void prepare(Map<String, Object> topoConf, TopologyContext context, OutputCollector collector) {

        this.collector = collector;
        this.task_id = context.getThisTaskId();
        this.task = context.getThisComponentId()+" "+this.task_id;
        System.out.println("----- Started task: "+this.task);

        // for custom grouping example
        this.drop_task = context.getComponentTasks(context.getThisComponentId()).get(0);
    }

    public void execute(Tuple input) {

        String sourcetext = input.getStringByField("words");
        Integer difficulty = input.getIntegerByField("difficulty");

        processed_tuples++;
        System.out.println("----- "+ this.task +
                " received "+ sourcetext +
                " from "+ input.getSourceComponent() + " " + input.getSourceTask() +
                " processed "+ processed_tuples);

        // custom grouping task example - filtering out some text
        if (task_id == drop_task) return;

        // the operator functionality for normal tasks
        String[] words = sourcetext.split(" ");
        for(String word : words) {
            this.collector.emit(new Values(word));
        }
    }

    public void declareOutputFields(OutputFieldsDeclarer declarer) {

        declarer.declare(new Fields("word"));
    }

}