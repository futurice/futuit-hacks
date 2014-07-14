import threading


class BlockingThreadPool():
    """
    Create threads, blocking if the number of active threads is at maximum.
    """

    def __init__(self, size):
        """
        size - the maximum number of threads that may exist at any time.
        """
        if size < 1:
            raise ValueError('Invalid size ' + str(size) + ' must be >= 1')
        self.__size = size
        self.__sem = threading.BoundedSemaphore(self.__size)
        # used to prevent a deadlock from multiple join() calls
        self.__joinLock = threading.Lock()

    def submit(self, work):
        """
        Submit work (a callable), blocking until more threads can be created.
        """
        self.__sem.acquire()

        def target():
            try:
                work()
            finally:
                self.__sem.release()
        threading.Thread(target=target).start()

    def join(self):
        """
        Wait for previously submitted work to finish before returning.

        If you call submit() before join() returns, the pool might still have
        work to do when join() returns. But all work submitted before calling
        join() will have completed.
        """
        # prevent deadlock in the case of several simultaneous calls to join()
        self.__joinLock.acquire()
        for i in range(self.__size):
            self.__sem.acquire()
        # the work submitted before this call to join() is now finished
        for i in range(self.__size):
            self.__sem.release()
        self.__joinLock.release()
