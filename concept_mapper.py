import networkx as nx
from pyvis.network import Network


def create_concept_map(data):

    net = Network(
        height="750px",
        width="100%",
        directed=True,
        bgcolor="#0f172a",
        font_color="white"
    )

    # -----------------------------
    # Hierarchical layout
    # -----------------------------

    net.set_options("""
    {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "UD",
          "sortMethod": "directed",
          "levelSeparation": 180,
          "nodeSpacing": 180,
          "treeSpacing": 250
        }
      },

      "physics": {
        "enabled": false
      },

      "nodes": {
        "shape": "box",
        "margin": 15,
        "widthConstraint": {
          "minimum": 150,
          "maximum": 220
        },
        "font": {
          "size": 18,
          "face": "Arial",
          "color": "#ffffff"
        },
        "borderWidth": 2,
        "shadow": true
      },

      "edges": {
        "arrows": {
          "to": {
            "enabled": true,
            "scaleFactor": 1.2
          }
        },
        "smooth": {
          "enabled": true,
          "type": "cubicBezier",
          "forceDirection": "vertical",
          "roundness": 0.4
        },
        "font": {
          "size": 13,
          "color": "#e2e8f0",
          "strokeWidth": 0
        },
        "width": 2
      },

      "interaction": {
        "hover": true,
        "dragNodes": true,
        "zoomView": true,
        "navigationButtons": true
      }
    }
    """)

    # -----------------------------
    # Add concept nodes
    # -----------------------------

    for concept in data["concepts"]:

        name = concept["name"]
        description = concept.get(
            "description",
            ""
        )

        concept_type = concept.get(
            "type",
            "Concept"
        )

        # Different sizes for different concept types
        if concept_type.lower() == "core concept":
            size = 35
        else:
            size = 28

        net.add_node(
            name,
            label=name,
            title=f"""
            <b>{name}</b><br><br>
            {description}<br><br>
            <b>Type:</b> {concept_type}
            """,
            size=size,
            color={
                "background": "#2563eb",
                "border": "#93c5fd",
                "highlight": {
                    "background": "#3b82f6",
                    "border": "#ffffff"
                }
            }
        )

    # -----------------------------
    # Add relationship arrows
    # -----------------------------

    for relation in data["relationships"]:

        source = relation["source"]
        target = relation["target"]

        relationship = relation.get(
            "relationship",
            "related to"
        )

        # Only add relationship if both nodes exist
        if source in [
            c["name"] for c in data["concepts"]
        ] and target in [
            c["name"] for c in data["concepts"]
        ]:

            net.add_edge(
                source,
                target,
                label=relationship,
                title=relationship,
                arrows="to"
            )

    return net