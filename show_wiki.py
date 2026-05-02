import json
import networkx as nx
from networkx.readwrite import json_graph
from pyvis.network import Network

with open('wiki/graph.json') as f:
    data = json.load(f)

# Reconstruir el grafo
#G = json_graph.node_link_graph(data)

# Visualizar (requiere matplotlib o pyvis)
#nx.draw(G, with_labels=True)

# 2. Reconstruir el grafo de NetworkX
G = nx.node_link_graph(data)

# 3. Crear la red de Pyvis
net = Network(notebook=True, directed=True, height="750px", width="100%")

# 4. Importar el grafo de NetworkX a Pyvis
net.from_nx(G)

# 5. Generar y abrir el archivo HTML
net.show("wiki.html")