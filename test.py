import dgl
import torch

graph = dgl.DGLGraph()

edges = [(0,1),(1,2),(2,3),(2,3)]

graph = dgl.add_edges(graph, u=0,v=1, etype=("node1", "int" ,"node2"))
# graph.edata['weight'].append(1)
print(graph.all_edges())
print(graph)
graph = dgl.add_edges(graph, u=1,v=2)
# graph.edata['weight'].append(1)
print(graph.all_edges())
print(graph)
graph = dgl.add_edges(graph, u=2,v=3)
# graph.edata['weight'].append(1)
print(graph.all_edges())
print(graph)

graph.edges["int"].data['weight'] = torch.Tensor([1,1,1])