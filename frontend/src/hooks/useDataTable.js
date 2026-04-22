import { useMemo, useState } from "react";

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
  const [rawPage, setRawPage] = useState(1);
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
  const page = Math.min(rawPage, totalPages);

  const setPage = (nextPage) => {
    setRawPage(() => {
      const value = typeof nextPage === "function" ? nextPage(page) : nextPage;
      return Math.min(Math.max(1, value), totalPages);
    });
  };

  const updatePageSize = (nextPageSize) => {
    setPageSize(nextPageSize);
    setRawPage(1);
  };

  const paginatedItems = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedItems.slice(start, start + pageSize);
  }, [page, pageSize, sortedItems]);

  const requestSort = (key) => {
    setRawPage(1);
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
    setPageSize: updatePageSize,
    totalPages,
    totalItems: sortedItems.length,
    paginatedItems,
  };
}

export default useDataTable;
