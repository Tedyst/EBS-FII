package ro.tedyst;

import java.util.Map;
import java.util.HashMap;

import org.apache.storm.task.OutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichBolt;
import org.apache.storm.tuple.Fields;
import org.apache.storm.tuple.Tuple;
import org.apache.storm.tuple.Values;

public class WordCountBolt extends BaseRichBolt {

    private static final long serialVersionUID = 3;

    private OutputCollector collector;
    private HashMap<String, Integer> count;
    private String task;

    // remove template type qualifiers from conf declaration for Storm v1
    public void prepare(Map<String, Object> topoConf, TopologyContext context, OutputCollector collector) {

        this.collector = collector;
        this.count = new HashMap<String, Integer>();
        this.task = context.getThisComponentId()+" "+context.getThisTaskId();
        System.out.println("----- Started task: "+this.task);

    }

    public void execute(Tuple input) {

        String word = input.getStringByField("word");
        Integer wordcount = this.count.get(word);

        System.out.println("----- "+ this.task +
                " received "+ word +
                " from "+ input.getSourceComponent() + " " + input.getSourceTask());

        if (wordcount == null) {
            wordcount = 0;
        }
        wordcount++;
        this.count.put(word, wordcount);
        this.collector.emit(new Values(word,wordcount));

    }

    public void declareOutputFields(OutputFieldsDeclarer declarer) {

        declarer.declare(new Fields("word","count"));

    }

}