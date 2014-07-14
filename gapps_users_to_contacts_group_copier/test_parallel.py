from parallel import BlockingThreadPool
import unittest

class TestBlockingThreadPool(unittest.TestCase):

    def testCreate(self):
        for sz in (1, 2):
            self.assertTrue(isinstance(BlockingThreadPool(sz),
                BlockingThreadPool))

        for sz in (0, -1):
            with self.assertRaises(ValueError):
                BlockingThreadPool(sz)

    def testJoin(self):
        # workaround because nested function can't assign to outer function's
        # variables in Python 2.
        holder = {
            'total': 0
        }
        n = 5
        sz = 3
        tp = BlockingThreadPool(sz)
        def work():
            holder['total'] += 1
        for i in range(n):
            tp.submit(work)
        tp.join()
        self.assertEqual(holder['total'], n)


if __name__ == '__main__':
    unittest.main()
