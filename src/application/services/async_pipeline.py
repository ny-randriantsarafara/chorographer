"""Async pipeline utilities for producer-consumer patterns.

This module provides utilities to overlap extraction (CPU-bound) with
database loading (I/O-bound) using asyncio.Queue.
"""

import asyncio
from collections.abc import Awaitable, Callable, Iterator
from typing import Generic, TypeVar

T = TypeVar("T")


class AsyncBatcher(Generic[T]):
    """Converts sync iterator to async batches via queue.

    Implements a producer-consumer pattern where:
    - Producer: Reads from sync iterator in executor (non-blocking)
    - Consumer: Processes batches asynchronously (e.g., DB writes)

    This allows extraction and loading to happen concurrently,
    improving overall pipeline throughput.

    Usage:
        async def save_batch(items: list[Road]) -> int:
            return await repository.save_roads_batch(items)

        batcher = AsyncBatcher(extractor.extract_roads(), batch_size=1000)
        total = await batcher.run(save_batch)
    """

    def __init__(
        self,
        iterator: Iterator[T],
        batch_size: int = 1000,
        max_queue_size: int = 10,
    ) -> None:
        """Initialize the async batcher.

        Args:
            iterator: Sync iterator to read from
            batch_size: Number of items per batch
            max_queue_size: Max batches to buffer (backpressure control)
        """
        self.iterator = iterator
        self.batch_size = batch_size
        self.queue: asyncio.Queue[list[T] | None] = asyncio.Queue(max_queue_size)
        self._producer_error: Exception | None = None

    def _iter_batches(self) -> list[T] | None:
        """Read next batch from iterator (runs in executor).

        Returns:
            List of items or None if iterator exhausted
        """
        batch: list[T] = []
        try:
            for item in self.iterator:
                batch.append(item)
                if len(batch) >= self.batch_size:
                    return batch
        except Exception as e:
            self._producer_error = e
            raise

        return batch if batch else None

    async def produce(self) -> None:
        """Producer: read from iterator and enqueue batches."""
        loop = asyncio.get_event_loop()

        while True:
            try:
                batch = await loop.run_in_executor(None, self._iter_batches)
            except Exception:
                # Signal consumer to stop on error
                await self.queue.put(None)
                return

            if batch is None:
                # Signal completion
                await self.queue.put(None)
                break

            await self.queue.put(batch)

    async def consume(
        self,
        processor: Callable[[list[T]], Awaitable[int]],
    ) -> int:
        """Consumer: process batches from queue.

        Args:
            processor: Async function that processes a batch and returns count

        Returns:
            Total items processed
        """
        total = 0
        while True:
            batch = await self.queue.get()
            if batch is None:
                break
            total += await processor(batch)
        return total

    async def run(
        self,
        processor: Callable[[list[T]], Awaitable[int]],
    ) -> int:
        """Run producer and consumer concurrently.

        Args:
            processor: Async function that processes a batch and returns count

        Returns:
            Total items processed

        Raises:
            Exception: Re-raises any producer error after consumer completes
        """
        producer = asyncio.create_task(self.produce())
        consumer = asyncio.create_task(self.consume(processor))

        # Wait for producer to finish (consumer will stop on None sentinel)
        await producer
        total = await consumer

        # Re-raise producer error if any
        if self._producer_error is not None:
            raise self._producer_error

        return total
