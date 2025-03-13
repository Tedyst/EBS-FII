package ro.tedyst;

import java.util.HashMap;
import java.util.Map;

import org.apache.storm.task.OutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichBolt;
import org.apache.storm.tuple.Tuple;

public class TerminalBolt extends BaseRichBolt {

    private HashMap<String, Integer> count;

    public void prepare(Map stormConf, TopologyContext context, OutputCollector collector) {
        // TODO Auto-generated method stub
        this.count = new HashMap<String, Integer>();

    }

    public void execute(Tuple input) {
        // TODO Auto-generated method stub
        String word = input.getStringByField("word");
        Integer count = input.getIntegerByField("count");
        this.count.put(word, count);

    }

    public void declareOutputFields(OutputFieldsDeclarer declarer) {
        // TODO Auto-generated method stub

    }

    public void cleanup() {
        System.out.println("Topology Result:");
        for (Map.Entry<String, Integer> entry : this.count.entrySet()) {
            System.out.println(entry.getKey()+" - "+entry.getValue());
        }
    }

}