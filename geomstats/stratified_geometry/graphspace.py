"""Graph Space.

Lead author: Anna Calissano.
"""

import networkx as nx

import geomstats.backend as gs
from geomstats.geometry.matrices import Matrices, MatricesMetric
from geomstats.stratified_geometry.stratified_spaces import (
    Point,
    PointSet,
    PointSetGeometry,
)


class Graph(Point):
    r"""Class for the Graph.

    Points are represented by :math:`nodes \times nodes` adjacency matrices.

    Parameters
    ----------
    nodes : int
        Number of graph nodes
    p : int
        Dimension of euclidean parameter or label associated to a graph.

    References
    ----------
    ..[Calissano2020]  Calissano, A., Feragen, A., Vantini, S.
              “Graph Space: Geodesic Principal Components for a Population of
              Network-valued Data.”
              Mox report 14, 2020.
              https://mox.polimi.it/reports-and-theses/publication-results/?id=855.
    """

    def __init__(self, adj, p=None):
        super(Graph).__init__()
        self.adj = adj
        self.p = p

    def __repr__(self):
        """Return a readable representation of the instance."""
        return f"Adjacency: {self.adj} Parameter: {self.p}"

    def __hash__(self):
        """Return the hash of the instance."""
        return hash((self.adj, self.p))

    def to_array(self):
        """Return the hash of the instance."""
        return gs.array([self.adj, self.p])

    def to_networkx(self):
        """Turn the graph into a networkx format."""
        return nx.from_numpy_matrix(self.adj)


def _graph_vectorize(fun):
    r"""Vectorize the input Graph Point to an array."""

    def wrapped(*args, **kwargs):
        r"""Vectorize the belongs."""
        args = list(args)
        if type(args[1]) not in [list, Graph]:
            return fun(*args, **kwargs)
        if type(args[1]) is Graph:
            args[1] = args[1].adj
            return fun(*args, **kwargs)
        args[1] = gs.array([graph.adj for graph in args[1]])
        return fun(*args, **kwargs)

    return wrapped


def _multiple_input_vectorize(fun):
    r"""Vectorize the input Graph Point to an array."""

    def _input_manipulation(args, index):
        r"""Check input type."""
        if type(args[index]) not in [list, Graph]:
            return args
        if type(args[index]) is Graph:
            args[index] = args[index].adj
            return args
        args[index] = gs.array([graph.adj for graph in args[index]])
        return args

    def wrapped(*args, **kwargs):
        r"""Vectorize the belongs."""
        args = list(args)
        args = _input_manipulation(args, 1)
        args = _input_manipulation(args, 2)
        return fun(*args, **kwargs)

    return wrapped


class GraphSpace(PointSet):
    r"""Class for the Graph Space.

    Graph Space to analyse populations of labelled and unlabelled graphs.
    The space focuses on graphs with scalar euclidean attributes on nodes and edges,
    with a finite number of nodes and both directed and undirected edges.
    For undirected graphs, use symmetric adjacency matrices. The space is a quotient
    space obtained by applying the permutation action of nodes to the space
    of adjacency matrices. Notice that for computation reasons the module works with
    both the gs.array representation of graph and the Graph(Point) representation.

    Points are represented by :math:`nodes \times nodes` adjacency matrices.
    Both the array input and the Graph Point type input work.

    Parameters
    ----------
    nodes : int
        Number of graph nodes
    total_space : space
        Total Space before applying the permutation action. Default: Adjacency Matrices.

    References
    ----------
    ..[Calissano2020]  Calissano, A., Feragen, A., Vantini, S.
              “Graph Space: Geodesic Principal Components for a Population of
              Network-valued Data.”
              Mox report 14, 2020.
              https://mox.polimi.it/reports-and-theses/publication-results/?id=855.
    """

    def __init__(self, nodes, total_space=Matrices):
        super(GraphSpace).__init__()
        self.nodes = nodes
        self.total_space = total_space(self.nodes, self.nodes)

    @_graph_vectorize
    def belongs(self, graphs, atol=gs.atol):
        r"""Check if the matrix is an adjacency matrix.

        The adjacency matrix should be associated to the
        graph with n nodes.

        Parameters
        ----------
        graphs : List of Graph type or array-like Adjecency Matrices.
                Points to be checked.
        atol : float
            Tolerance.
            Optional, default: backend atol.

        Returns
        -------
        belongs : array-like, shape=[...,n]
            Boolean denoting if graph belongs to the space.
        """
        return self.total_space.belongs(graphs, atol=atol)

    def random_point(self, n_samples=1, bound=1.0):
        r"""Sample in Graph Space.

        Parameters
        ----------
        n_samples : int
            Number of samples.
            Optional, default: 1.
        bound : float
            Bound of the interval in which to sample in the tangent space.
            Optional, default: 1.

        Returns
        -------
        graph_samples : array-like, shape=[..., n, n]
            Points sampled in GraphSpace(n).
        """
        return self.total_space.random_point(n_samples=n_samples, bound=bound)

    @_graph_vectorize
    def set_to_array(self, points):
        r"""Sample in Graph Space.

        Parameters
        ----------
        points : List of Graph type or array-like Adjacency Matrices.
                Points to be turned into an array
        Returns
        -------
        graph_array : array-like, shape=[..., nodes, nodes]
                An array containing all the Graphs.
        """
        return points

    @_graph_vectorize
    def to_networkx(self, points):
        r"""Turn point into a networkx object.

        Parameters
        ----------
        points : List of Graph type or array-like Adjacency Matrices.

        Returns
        -------
        nx_list : list of Networkx object
                An array containing all the Graphs.
        """
        if points.shape == (self.nodes, self.nodes):
            return nx.from_numpy_matrix(points)
        return [nx.from_numpy_matrix(point) for point in points]

    @_graph_vectorize
    def permute(self, graph_to_permute, permutation):
        r"""Permutation action applied to graph observation.

        Parameters
        ----------
        graph_to_permute : List of Graph type or array-like Adjacency Matrices.
            Input graphs to be permuted.
        permutation: array-like, shape=[..., n]
            Node permutations where in position i we have the value j meaning
            the node i should be permuted with node j.

        Returns
        -------
        graphs_permuted : array-like, shape=[..., n, n]
            Graphs permuted.
        """
        nodes = self.nodes
        single_graph = len(graph_to_permute.shape) < 3
        if single_graph:
            graph_to_permute = [graph_to_permute]
            permutation = [permutation]
        result = []
        for i, p in enumerate(permutation):
            if gs.all(gs.array(nodes) == gs.array(p)):
                result.append(graph_to_permute[i])
            else:
                gtype = graph_to_permute[i].dtype
                permutation_matrix = gs.array_from_sparse(
                    data=gs.ones(nodes, dtype=gtype),
                    indices=list(zip(list(range(nodes)), p)),
                    target_shape=(nodes, nodes),
                )
                result.append(
                    self.total_space.mul(
                        permutation_matrix,
                        graph_to_permute[i],
                        gs.transpose(permutation_matrix),
                    )
                )
        return result[0] if single_graph else gs.array(result)


class GraphSpaceGeometry(PointSetGeometry):
    """Quotient metric on the graph space.

    Parameters
    ----------
    nodes : int
        Number of nodes
    """

    def __init__(self, space, total_space_metric=MatricesMetric):
        self.space = space
        self.total_space_metric = total_space_metric(self.nodes, self.nodes)

    @property
    def nodes(self):
        r"""Save the number of nodes."""
        return self.space.nodes

    @_multiple_input_vectorize
    def dist(self, graph_a, graph_b, matcher="ID"):
        """Compute distance between two equivalence classes.

        Compute the distance between two equivalence classes of
        adjacency matrices [Jain2009]_.

        Parameters
        ----------
        graph_a : List of Graph type or array-like Adjacency Matrices.
        graph_b : List of Graph type or array-like Adjacency Matrices.
        matcher : selecting which matcher to use
            'FAQ': [Vogelstein2015]_ Fast Quadratic Assignment
            note: use Frobenius metric in background.

        Returns
        -------
        distance : array-like, shape=[...,]
            distance between equivalence classes.

        References
        ----------
        ..[Jain2009]  Jain, B., Obermayer, K.
                  "Structure Spaces." Journal of Machine Learning Research 10.11 (2009).
                  https://www.jmlr.org/papers/v10/jain09a.html.
        ..[Vogelstein2015] Vogelstein JT, Conroy JM, Lyzinski V, Podrazik LJ,
                Kratzer SG, Harley ET, Fishkind DE, Vogelstein RJ, Priebe CE.
                “Fast approximate quadratic programming for graph matching.“
                PLoS One. 2015 Apr 17; doi: 10.1371/journal.pone.0121002.
        """
        if graph_a.ndim > graph_b.ndim:
            base_graph = graph_b
            graph_to_permute = graph_a
        else:
            base_graph = graph_a
            graph_to_permute = graph_b
        if matcher == "FAQ":
            perm = self.faq_matching(base_graph, graph_to_permute)
        if matcher == "ID":
            print(base_graph)
            print(graph_to_permute)

            perm = self.id_matching(base_graph, graph_to_permute)
        return self.total_space_metric.dist(
            base_graph,
            self.space.permute(graph_to_permute, perm),
        )

    @_multiple_input_vectorize
    def geodesic(self, base_point, end_point, matcher="ID"):
        """Compute distance between two equivalence classes.

        Compute the distance between two equivalence classes of
        adjacency matrices [Jain2009]_.

        Parameters
        ----------
        base_point : List of Graph type or array-like Adjacency Matrices.
            Start .
        end_point : List of Graph type or array-like Adjacency Matrices.
            Second graph to align to the first graph.
        matcher : selecting which matcher to use
            'FAQ': [Vogelstein2015]_ Fast Quadratic Assignment
            note: use Frobenius metric in background.

        Returns
        -------
        distance : array-like, shape=[...,]
            distance between equivalence classes.

        References
        ----------
        ..[Jain2009]  Jain, B., Obermayer, K.
                  "Structure Spaces." Journal of Machine Learning Research 10.11 (2009).
                  https://www.jmlr.org/papers/v10/jain09a.html.
        ..[Vogelstein2015] Vogelstein JT, Conroy JM, Lyzinski V, Podrazik LJ,
                Kratzer SG, Harley ET, Fishkind DE, Vogelstein RJ, Priebe CE.
                “Fast approximate quadratic programming for graph matching.“
                PLoS One. 2015 Apr 17; doi: 10.1371/journal.pone.0121002.
        """
        if matcher == "FAQ":
            perm = self.faq_matching(base_point, end_point)
        if matcher == "ID":
            perm = self.id_matching(base_point, end_point)
        return self.total_space_metric.geodesic(
            base_point, self.space.permute(end_point, perm)
        )

    @staticmethod
    def faq_matching(base_graph, graph_to_permute):
        """Fast Quadratic Assignment for graph matching.

        Parameters
        ----------
        base_graph : array-like, shape=[..., n, n]
        First graph.
        graph_to_permute : array-like, shape=[..., n, n]
        Second graph to align.

        Returns
        -------
        permutation : array-like, shape=[...,n]
            node permutation indexes of the second graph.

        References
        ----------
        ..[Vogelstein2015] Vogelstein JT, Conroy JM, Lyzinski V, Podrazik LJ,
                Kratzer SG, Harley ET, Fishkind DE, Vogelstein RJ, Priebe CE.
                “Fast approximate quadratic programming for graph matching.“
                PLoS One. 2015 Apr 17; doi: 10.1371/journal.pone.0121002.
        """
        l_base = len(base_graph.shape)
        l_obj = len(graph_to_permute.shape)
        if l_base == l_obj == 3:
            return [
                gs.linalg.quadratic_assignment(x, y, options={"maximize": True})
                for x, y in zip(base_graph, graph_to_permute)
            ]
        if l_base == l_obj == 2:
            return gs.linalg.quadratic_assignment(
                base_graph, graph_to_permute, options={"maximize": True}
            )
        if l_base < l_obj:
            return [
                gs.linalg.quadratic_assignment(x, y, options={"maximize": True})
                for x, y in zip(
                    gs.stack([base_graph] * graph_to_permute.shape[0]), graph_to_permute
                )
            ]
        raise ValueError(
            "Align a set of graphs to one graphs,"
            "Pass the single graphs as base_graph"
        )

    def id_matching(self, base_graph, graph_to_permute):
        """Identity matching.

        Parameters
        ----------
        base_graph : array-like, shape=[..., n, n]
        First graph.
        graph_to_permute : array-like, shape=[..., n, n]
        Second graph to align.

        Returns
        -------
        permutation : array-like, shape=[...,n]
            node permutation indexes of the second graph.
        """
        l_base = len(base_graph.shape)
        l_obj = len(graph_to_permute.shape)
        if l_base == l_obj == 3 or l_base < l_obj:
            return [list(range(self.nodes))] * len(graph_to_permute)
        if l_base == l_obj == 2:
            return list(range(self.nodes))
        raise (
            ValueError(
                "The method can align a set of graphs to one graphs,"
                "but the single graphs should be passed as base_graph"
            )
        )
