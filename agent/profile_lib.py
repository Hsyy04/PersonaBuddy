import os
import json

import networkx as nx


class ProfileLib:
    def __init__(self, num_users, profile_dir, load=False):
        self.num_users, self.profile_dir = num_users, profile_dir
        self.user_graphs = self._load_all_graphs()     if load else {user_id: nx.DiGraph() for user_id in range(num_users)}
        self.page_ranks  = self._load_all_page_ranks() if load else {user_id: dict() for user_id in range(num_users)}
    
    # Train
    def add_edge(self, user_id, start, end, weight=1):
        if self.user_graphs[user_id].has_edge(start, end):
            self.user_graphs[user_id][start][end]['weight'] += weight
        else:
            self.user_graphs[user_id].add_edge(start, end, weight=weight)
    
    def process_and_save(self):
        os.makedirs(self.profile_dir)
        self._save_all_graphs()
        self._calculate_and_save_all_page_ranks()
        self._visualize_and_save_all_graphs()

    # Graph
    def _save_all_graphs(self):
        for user_id, graph in self.user_graphs.items():
            nx.write_gml(graph, os.path.join(self.profile_dir, f'user_{user_id}.gml'))

    def _load_all_graphs(self):
        user_graphs = dict()
        for user_id in range(self.num_users):
            user_graphs[user_id] = nx.read_gml(os.path.join(self.profile_dir, f'user_{user_id}.gml'))
        return user_graphs


if __name__ == '__main__':
    num_users = 3
    my_profile_lib = ProfileLib(num_users, profile_dir='profile', load=False)

    for user_id in range(num_users):
        my_profile_lib.add_edge(user_id, 'A', 'B', weight=1)
        my_profile_lib.add_edge(user_id, 'A', 'C', weight=2)
    my_profile_lib.process_and_save()

    for user_id in range(num_users):
        print(f"Edges for user {user_id}:")
        for edge in my_profile_lib.user_graphs[user_id].edges(data=True):
            print(edge)

    for user_id, pagerank in my_profile_lib.page_ranks.items():
        print(f"User {user_id}: {pagerank}")