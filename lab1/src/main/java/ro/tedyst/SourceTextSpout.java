package ro.tedyst;

import java.util.Map;

import org.apache.storm.spout.SpoutOutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichSpout;
import org.apache.storm.tuple.Fields;
import org.apache.storm.tuple.Values;

public class SourceTextSpout extends BaseRichSpout {

    private SpoutOutputCollector collector;
    private String[] sourcetext = {
            "text one",
            "text two",
            "text three",
            "text four",
            "too much text after one"
    };
    private int i = 0;

    public void open(Map <String,Object> conf, TopologyContext context, SpoutOutputCollector collector) {
        // TODO Auto-generated method stub
        this.collector = collector;

    }

    public void nextTuple() {
        // TODO Auto-generated method stub

        this.collector.emit(new Values(sourcetext[i]));
        i++;
        if (i >= sourcetext.length) {
            i = 0;
        }

        try {
            Thread.sleep(1);
        } catch (InterruptedException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
    }

    public void declareOutputFields(OutputFieldsDeclarer declarer) {
        // TODO Auto-generated method stub
        declarer.declare(new Fields("words"));

    }

}
