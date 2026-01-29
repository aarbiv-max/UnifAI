/**
 * Reusable Data Structures
 * 
 * This module contains general-purpose data structures that can be used
 * across the application.
 */

// ============================================================================
// MinHeap - Priority Queue
// ============================================================================

/**
 * Item stored in the MinHeap with a key and score.
 */
export interface HeapItem<T = string> {
  key: T;
  score: number;
}

/**
 * Min-heap (priority queue) implementation for efficient retrieval of
 * minimum-scored items.
 * 
 * Time Complexity:
 * - push: O(log n)
 * - pop: O(log n)
 * - peek: O(1)
 * - size: O(1)
 * 
 * Use Cases:
 * - A* pathfinding (finding next node with lowest f-score)
 * - Dijkstra's algorithm
 * - Task scheduling by priority
 * 
 * @example
 * ```ts
 * const heap = new MinHeap<string>();
 * heap.push({ key: 'task-a', score: 5 });
 * heap.push({ key: 'task-b', score: 2 });
 * heap.push({ key: 'task-c', score: 8 });
 * 
 * console.log(heap.pop()); // { key: 'task-b', score: 2 }
 * console.log(heap.pop()); // { key: 'task-a', score: 5 }
 * ```
 */
export class MinHeap<T = string> {
  private items: HeapItem<T>[] = [];

  /**
   * Returns the number of items in the heap.
   */
  get size(): number {
    return this.items.length;
  }

  /**
   * Returns true if the heap is empty.
   */
  get isEmpty(): boolean {
    return this.items.length === 0;
  }

  /**
   * Returns the minimum item without removing it.
   * Returns undefined if the heap is empty.
   */
  peek(): HeapItem<T> | undefined {
    return this.items[0];
  }

  /**
   * Adds an item to the heap.
   * @param item - The item to add with its score.
   */
  push(item: HeapItem<T>): void {
    this.items.push(item);
    this.bubbleUp(this.items.length - 1);
  }

  /**
   * Removes and returns the minimum item from the heap.
   * Returns undefined if the heap is empty.
   */
  pop(): HeapItem<T> | undefined {
    if (this.items.length === 0) return undefined;
    
    const top = this.items[0];
    const last = this.items.pop();
    
    if (this.items.length > 0 && last) {
      this.items[0] = last;
      this.bubbleDown(0);
    }
    
    return top;
  }

  /**
   * Clears all items from the heap.
   */
  clear(): void {
    this.items = [];
  }

  /**
   * Restores heap property by moving an item up.
   */
  private bubbleUp(index: number): void {
    let currentIndex = index;
    
    while (currentIndex > 0) {
      const parentIndex = Math.floor((currentIndex - 1) / 2);
      
      if (this.items[parentIndex].score <= this.items[currentIndex].score) {
        break;
      }
      
      // Swap with parent
      [this.items[parentIndex], this.items[currentIndex]] = [
        this.items[currentIndex],
        this.items[parentIndex],
      ];
      currentIndex = parentIndex;
    }
  }

  /**
   * Restores heap property by moving an item down.
   */
  private bubbleDown(index: number): void {
    let currentIndex = index;
    const length = this.items.length;
    
    while (true) {
      const leftIndex = currentIndex * 2 + 1;
      const rightIndex = currentIndex * 2 + 2;
      let smallestIndex = currentIndex;

      if (
        leftIndex < length &&
        this.items[leftIndex].score < this.items[smallestIndex].score
      ) {
        smallestIndex = leftIndex;
      }

      if (
        rightIndex < length &&
        this.items[rightIndex].score < this.items[smallestIndex].score
      ) {
        smallestIndex = rightIndex;
      }

      if (smallestIndex === currentIndex) {
        break;
      }

      // Swap with smallest child
      [this.items[currentIndex], this.items[smallestIndex]] = [
        this.items[smallestIndex],
        this.items[currentIndex],
      ];
      currentIndex = smallestIndex;
    }
  }
}

// ============================================================================
// Additional Data Structures (for future use)
// ============================================================================

/**
 * Simple Union-Find (Disjoint Set Union) data structure.
 * Useful for cycle detection and connected component analysis.
 */
export class UnionFind {
  private parent: Map<string, string> = new Map();
  private rank: Map<string, number> = new Map();

  /**
   * Finds the root representative of the set containing the element.
   * Uses path compression for efficiency.
   */
  find(x: string): string {
    if (!this.parent.has(x)) {
      this.parent.set(x, x);
      this.rank.set(x, 0);
    }

    if (this.parent.get(x) !== x) {
      // Path compression
      this.parent.set(x, this.find(this.parent.get(x)!));
    }

    return this.parent.get(x)!;
  }

  /**
   * Unions the sets containing elements x and y.
   * Uses union by rank for efficiency.
   * @returns true if the sets were different (and thus merged)
   */
  union(x: string, y: string): boolean {
    const rootX = this.find(x);
    const rootY = this.find(y);

    if (rootX === rootY) {
      return false; // Already in same set
    }

    const rankX = this.rank.get(rootX) || 0;
    const rankY = this.rank.get(rootY) || 0;

    if (rankX < rankY) {
      this.parent.set(rootX, rootY);
    } else if (rankX > rankY) {
      this.parent.set(rootY, rootX);
    } else {
      this.parent.set(rootY, rootX);
      this.rank.set(rootX, rankX + 1);
    }

    return true;
  }

  /**
   * Checks if two elements are in the same set.
   */
  connected(x: string, y: string): boolean {
    return this.find(x) === this.find(y);
  }
}
