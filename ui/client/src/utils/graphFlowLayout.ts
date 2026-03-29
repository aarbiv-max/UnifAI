import { Position } from '@reactflow/core';

const nodeWidth = 200;
const nodeHeight = 50;

export const initialNodePosition = {
    x: 0,
    y: 0,
};

export const getLayoutedElements = (nodes: any[], edges: any[], direction = 'TB') => {
    const dagre = require('dagre');
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({
        width: 200,
        height: 20,
    }));

    dagreGraph.setGraph({
        rankdir: direction,
    });

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, {
            width: nodeWidth,
            height: nodeHeight,
        });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    nodes.forEach((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        node.targetPosition = direction === 'LR' ? Position.Left : Position.Top;
        node.sourcePosition = direction === 'LR' ? Position.Right : Position.Bottom;

        // unfortunately we need this little hack to pass the information about the node size
        // so React Flow can handle the updates properly.
        node.style = {
            ...node.style,
            width: nodeWithPosition.width,
            height: nodeWithPosition.height,
        };

        node.position = {
            x: nodeWithPosition.x - nodeWidth / 2,
            y: nodeWithPosition.y - nodeHeight / 2,
        };

        return node;
    });

    return { layoutedNodes: nodes, layoutedEdges: edges };
};