import { useEffect, useMemo, useState } from "react";

function normalizeValue(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }

  if (typeof value === "number") {
    return value;
  }

  const asDate = new Date(value);
  if (!Number.isNaN(asDate.getTime()) && typeof value === "string" && value.includes("-")) {
    return asDate.getTime();
  }

  return String(value).toLowerCase();
}

export function useDataTable(items, options = {}) {
  const {
    initialSort = null,
    initialPageSize = 10,
    accessors = {},
  } = options;

  const [sortConfig, setSortConfig] = useState(initialSort);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const sortedItems = useMemo(() => {
    if (!sortConfig?.key) {
      return items;
    }

    const accessor = accessors[sortConfig.key];

    return [...items].sort((left, right) => {
      const leftValue = normalizeValue(accessor ? accessor(left) : left[sortConfig.key]);
      const rightValue = normalizeValue(accessor ? accessor(right) : right[sortConfig.key]);

      if (leftValue < rightValue) {
        return sortConfig.direction === "asc" ? -1 : 1;
      }

      if (leftValue > rightValue) {
        return sortConfig.direction === "asc" ? 1 : -1;
      }

      return 0;
    });
  }, [accessors, items, sortConfig]);

  const totalPages = Math.max(1, Math.ceil(sortedItems.length / pageSize));

  useEffect(() => {
    setPage(1);
  }, [items.length, pageSize, sortConfig]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  const paginatedItems = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedItems.slice(start, start + pageSize);
  }, [page, pageSize, sortedItems]);

  const requestSort = (key) => {
    setSortConfig((current) => {
      if (!current || current.key !== key) {
        return { key, direction: "asc" };
      }

      return {
        key,
        direction: current.direction === "asc" ? "desc" : "asc",
      };
    });
  };

  return {
    sortConfig,
    requestSort,
    page,
    setPage,
    pageSize,
    setPageSize,
    totalPages,
    totalItems: sortedItems.length,
    paginatedItems,
  };
}

export default useDataTable;
