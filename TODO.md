# TODO

* Go through file one by one to remove comments, lint and remove redundancies
* Push to github

Chunk -> extract -> dedup -> persist
    dedup as an abstraction in the add methods?

How to prune dedup? i.e. how to not run dedup on all extracted nodes and edges?
Perhaps do a similarity search for vectors that are close enough

Optional:

* Entity type dedup similar to relation dedup for extraction purposes
* Remove the tool call for the final answer and instead just let the agent respond
* Modify visualize to just take in the start node. It should visualize that node and it's immediate neighbours, that's it. It's should use graphviz or something.
* Batch embeddings
* Try to remove the tool dependencies from the OpenAI client
* Remove in memory cache from graph