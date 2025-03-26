package ro.tedyst;

import org.apache.storm.Config;
import org.apache.storm.LocalCluster;
import org.apache.storm.generated.StormTopology;
import org.apache.storm.topology.TopologyBuilder;
import org.apache.storm.tuple.Fields;


public class Main
{
    private static final String SPOUT_ID = "source_text_spout";
    private static final String SPLIT_BOLT_ID = "split_bolt";
    private static final String COUNT_BOLT_ID = "count_bolt";
    private static final String TERMINAL_BOLT_ID = "terminal_bolt";

    public static void main( String[] args ) throws Exception
    {
        TopologyBuilder builder = new TopologyBuilder();
        SourceTextSpout spout = new SourceTextSpout();
        SplitTextBolt splitbolt = new SplitTextBolt();
        WordCountBolt countbolt = new WordCountBolt();
        TerminalBolt terminalbolt = new TerminalBolt();

//    	builder.setSpout(SPOUT_ID, spout);
        builder.setSpout(SPOUT_ID, spout, 2);

//    	builder.setBolt(SPLIT_BOLT_ID, splitbolt).shuffleGrouping(SPOUT_ID);
//    	builder.setBolt(SPLIT_BOLT_ID, splitbolt, 2).setNumTasks(4).shuffleGrouping(SPOUT_ID);
//    	builder.setBolt(SPLIT_BOLT_ID, splitbolt, 2).setNumTasks(4).allGrouping(SPOUT_ID);
        builder.setBolt(SPLIT_BOLT_ID, splitbolt, 2).setNumTasks(4).customGrouping(SPOUT_ID, new LoadBalancerGrouping());

//    	builder.setBolt(COUNT_BOLT_ID, countbolt).fieldsGrouping(SPLIT_BOLT_ID, new Fields("word"));
        builder.setBolt(COUNT_BOLT_ID, countbolt, 4).fieldsGrouping(SPLIT_BOLT_ID, new Fields("word"));

        builder.setBolt(TERMINAL_BOLT_ID, terminalbolt).globalGrouping(COUNT_BOLT_ID);

        Config config = new Config();

        LocalCluster cluster = new LocalCluster();
        StormTopology topology = builder.createTopology();

        // fine tuning
        config.put(Config.TOPOLOGY_EXECUTOR_RECEIVE_BUFFER_SIZE,1024);
        // for Storm v1 use TOPOLOGY_DISRUPTOR_BATCH_SIZE
        config.put(Config.TOPOLOGY_TRANSFER_BATCH_SIZE,1);

        cluster.submitTopology("count_topology", config, topology);

        try {
            Thread.sleep(20000);
        } catch (InterruptedException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }

        cluster.killTopology("count_topology");
        cluster.shutdown();

        // comment this for Storm v1
        cluster.close();

    }
}