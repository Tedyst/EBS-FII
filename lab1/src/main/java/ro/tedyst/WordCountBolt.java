package ro.tedyst;
import java.util.HashMap;
import java.util.Map;

import org.apache.storm.task.OutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichBolt;
import org.apache.storm.tuple.Fields;
import org.apache.storm.tuple.Tuple;
import org.apache.storm.tuple.Values;

public class WordCountBolt extends BaseRichBolt {

    private OutputCollector collector;
    private HashMap<String, Integer> count;

    public void prepare(Map stormConf, TopologyContext context, OutputCollector collector) {
        // TODO Auto-generated method stub
        this.collector = collector;
        this.count = new HashMap<String, Integer>();

    }

    public void execute(Tuple input) {
        // TODO Auto-generated method stub
        String word = input.getStringByField("word");
        Integer wordcount = this.count.get(word);

        if (wordcount == null) {
            wordcount = 0;
        }
        wordcount++;
        this.count.put(word, wordcount);
        this.collector.emit(new Values(word,wordcount));
    }

    public void declareOutputFields(OutputFieldsDeclarer declarer) {
        // TODO Auto-generated method stub
        declarer.declare(new Fields("word","count"));
    }


}