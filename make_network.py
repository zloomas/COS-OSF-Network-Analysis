import pandas as pd
from network_functions import create_network, assign_edge_type


nodes, edges = create_network()

staff_ids = nodes[nodes.is_cos.notna()].guid.values
nodes['is_cos'] = nodes['is_cos'].fillna(2).astype(int)

edges_summary = edges.groupby(['user_a', 'user_b']).count().reset_index()

close_connections = edges_summary[edges_summary.project_guid > 1].reset_index(drop=True).copy()
close_connections['edge_type'] = close_connections.apply(lambda row: assign_edge_type(row, staff_ids), axis=1)


