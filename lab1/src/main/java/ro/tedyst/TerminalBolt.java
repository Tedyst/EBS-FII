package ro.tedyst;

import java.util.HashMap;
import java.util.Map;

import java.util.HashMap;
import java.util.Map;

import org.apache.storm.task.OutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichBolt;
import org.apache.storm.tuple.Tuple;

public class TerminalBolt extends BaseRichBolt {

    private static final long serialVersionUID = 4;

    private HashMap<String, Integer> count;

    // remove template type qualifiers from conf declaration for Storm v1
    public void prepare(Map<String, Object> topoConf, TopologyContext context, OutputCollector collector) {

        this.count = new HashMap<String, Integer>();
    }

    public void execute(Tuple input) {

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