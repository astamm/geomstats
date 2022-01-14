"""Unit tests for the manifold of matrices."""

import geomstats.backend as gs
import geomstats.tests
from geomstats.geometry.matrices import Matrices


class TestMatrices(geomstats.tests.TestCase):
    def setup_method(self):
        gs.random.seed(1234)

        self.m = 2
        self.n = 3
        self.space = Matrices(m=self.n, n=self.n)
        self.space_nonsquare = Matrices(m=self.m, n=self.n)
        self.metric = self.space.metric
        self.n_samples = 2

    @geomstats.tests.np_and_autograd_only
    def test_transpose(self):
        tr = self.space.transpose
        ar = gs.array
        a = gs.eye(3, 3, 1)
        b = gs.eye(3, 3, -1)
        self.assertAllClose(tr(a), b)
        self.assertAllClose(tr(ar([a, b])), ar([b, a]))

    @geomstats.tests.np_autograd_and_torch_only
    def test_make_symmetric(self):
        sym_mat = gs.array([[1.0, 2.0], [2.0, 1.0]])
        result = self.space.to_symmetric(sym_mat)
        expected = sym_mat
        self.assertAllClose(result, expected)

        mat = gs.array([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0], [3.0, 1.0, 1.0]])
        result = self.space.to_symmetric(mat)
        expected = gs.array([[1.0, 1.0, 3.0], [1.0, 0.0, 0.5], [3.0, 0.5, 1.0]])
        self.assertAllClose(result, expected)

        mat = gs.array(
            [[1e100, 1e-100, 1e100], [1e100, 1e-100, 1e100], [1e-100, 1e-100, 1e100]]
        )
        result = self.space.to_symmetric(mat)

        res = 0.5 * (1e100 + 1e-100)

        expected = gs.array([[1e100, res, res], [res, 1e-100, res], [res, res, 1e100]])
        self.assertAllClose(result, expected)

    @geomstats.tests.np_autograd_and_tf_only
    def test_make_symmetric_and_is_symmetric_vectorization(self):
        points = gs.array([[[1.0, 2.0], [3.0, 4.0]], [[5.0, 6.0], [4.0, 9.0]]])

        sym_points = self.space.to_symmetric(points)
        result = gs.all(self.space.is_symmetric(sym_points))
        expected = True
        self.assertAllClose(result, expected)

    def test_inner_product(self):
        base_point = gs.array([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0], [3.0, 1.0, 1.0]])

        tangent_vector_1 = gs.array(
            [[1.0, 2.0, 3.0], [0.0, -10.0, 0.0], [30.0, 1.0, 1.0]]
        )

        tangent_vector_2 = gs.array([[1.0, 4.0, 3.0], [5.0, 0.0, 0.0], [3.0, 1.0, 1.0]])

        result = self.metric.inner_product(
            tangent_vector_1, tangent_vector_2, base_point=base_point
        )

        expected = gs.trace(gs.matmul(gs.transpose(tangent_vector_1), tangent_vector_2))

        self.assertAllClose(result, expected)

    def test_cong(self):
        base_point = gs.array([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0], [3.0, 1.0, 1.0]])

        tangent_vector = gs.array(
            [[1.0, 2.0, 3.0], [0.0, -10.0, 0.0], [30.0, 1.0, 1.0]]
        )

        result = self.space.congruent(tangent_vector, base_point)
        expected = gs.matmul(tangent_vector, gs.transpose(base_point))
        expected = gs.matmul(base_point, expected)

        self.assertAllClose(result, expected)

    def test_norm(self):
        for n_samples in [1, 2]:
            mat = self.space.random_point(n_samples)
            result = self.metric.norm(mat)
            expected = self.space.frobenius_product(mat, mat) ** 0.5
            self.assertAllClose(result, expected)

    def test_flatten_reshape(self):
        matrix_list = self.space_nonsquare.random_point(n_samples=1)
        result = self.space_nonsquare.reshape(self.space_nonsquare.flatten(matrix_list))
        self.assertAllClose(result, matrix_list)

        matrix_list = self.space_nonsquare.random_point(n_samples=2)
        result = self.space_nonsquare.reshape(self.space_nonsquare.flatten(matrix_list))
        self.assertAllClose(result, matrix_list)

    def test_diagonal(self):
        mat = gs.eye(3)
        result = Matrices.diagonal(mat)
        expected = gs.ones(3)
        self.assertAllClose(result, expected)

        mat = gs.stack([mat] * 2)
        result = Matrices.diagonal(mat)
        expected = gs.ones((2, 3))
        self.assertAllClose(result, expected)