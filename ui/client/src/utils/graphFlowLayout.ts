export const dagreLayout = (elements: any[], direction = 'LR'): any[] => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setGraph({ rankdir: direction, ... });
  dagreGraph.setDefaultEdgeLabel(function() { return {}; });

  elements.forEach((el) => {
    if (el.id && el.position) {
      dagreGraph.setNode(el.id, { width: 150, height: 50 });
    }
  });

  dagre.layout(dagreGraph);

  return elements.map((el) => {
    if (el.id && el.position) {
      const node = dagreGraph.node(el.id);
      return { ...el, targetPosition: 'top', sourcePosition: 'bottom',
        position: { x: node.x - 75, y: node.y - 25 } };
    } else {
      return el
    }
  });
};