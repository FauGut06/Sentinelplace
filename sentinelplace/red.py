"""Red de ejemplo: grafo dirigido con probabilidades de movimiento lateral.

Cada arista (u, v) tiene p = probabilidad de que un atacante en u logre pasar a v.
Los nodos tienen un rol:
  - "entrada": punto de origen del atacante (no admite sensor)
  - "candidato": nodo donde se puede instalar un sensor, con su costo
  - "objetivo": activo critico, con su criticidad (no admite sensor: detectar
    en el propio activo ya es demasiado tarde)
"""
import networkx as nx

NODOS = {
    # nombre: (rol, zona, costo del sensor o criticidad)
    "internet": ("entrada", "externa", None),
    "web": ("candidato", "DMZ", 3),
    "correo": ("candidato", "DMZ", 3),
    "vpn": ("candidato", "DMZ", 2),
    "pc1": ("candidato", "usuarios", 1),
    "pc2": ("candidato", "usuarios", 1),
    "nucleo": ("candidato", "nucleo", 5),
    "app": ("candidato", "servidores", 2),
    "archivos": ("candidato", "servidores", 2),
    "salto": ("candidato", "servidores", 2),
    "bd": ("objetivo", "critica", 10),
    "dc": ("objetivo", "critica", 10),
    "respaldo": ("objetivo", "critica", 6),
}

ARISTAS = [
    # (origen, destino, probabilidad de exito)
    ("internet", "web", 0.6), ("internet", "correo", 0.5), ("internet", "vpn", 0.3),
    ("correo", "pc1", 0.6), ("correo", "pc2", 0.6),
    ("web", "app", 0.5), ("web", "nucleo", 0.3),
    ("vpn", "nucleo", 0.6), ("vpn", "salto", 0.4),
    ("pc1", "nucleo", 0.5), ("pc2", "nucleo", 0.5),
    ("pc1", "archivos", 0.4), ("pc2", "salto", 0.3),
    ("nucleo", "app", 0.5), ("nucleo", "archivos", 0.5),
    ("nucleo", "salto", 0.4), ("nucleo", "dc", 0.2),
    ("app", "bd", 0.6),
    ("archivos", "respaldo", 0.5), ("archivos", "dc", 0.3),
    ("salto", "dc", 0.6), ("salto", "bd", 0.5), ("salto", "respaldo", 0.4),
]


def construir_red() -> nx.DiGraph:
    """Crea el grafo dirigido de la red con sus atributos."""
    g = nx.DiGraph()
    for nombre, (rol, zona, valor) in NODOS.items():
        g.add_node(nombre, rol=rol, zona=zona,
                   costo=valor if rol == "candidato" else None,
                   criticidad=valor if rol == "objetivo" else None)
    for u, v, p in ARISTAS:
        g.add_edge(u, v, p=p)
    return g
