function TableControls({
  page,
  totalPages,
  pageSize,
  setPage,
  setPageSize,
  totalItems,
  itemLabel = "itens",
}) {
  const startItem = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, totalItems);

  return (
    <div className="flex flex-col gap-4 border-t border-slate-200/80 px-4 py-4 md:flex-row md:items-center md:justify-between">
      <p className="text-sm text-slate-500">
        Exibindo <span className="font-semibold text-slate-800">{startItem}</span> a{" "}
        <span className="font-semibold text-slate-800">{endItem}</span> de{" "}
        <span className="font-semibold text-slate-800">{totalItems}</span> {itemLabel}
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <select
          value={pageSize}
          onChange={(e) => setPageSize(Number(e.target.value))}
          className="rounded-2xl border border-slate-200 bg-white/90 px-3 py-2 text-sm text-slate-700"
        >
          <option value={10}>10 por página</option>
          <option value={20}>20 por página</option>
          <option value={50}>50 por página</option>
        </select>

        <div className="flex items-center gap-2">
          <button type="button" onClick={() => setPage(page - 1)} disabled={page <= 1} className="btn-secondary px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50">
            Anterior
          </button>
          <span className="text-sm text-slate-600">
            Página {page} de {totalPages}
          </span>
          <button type="button" onClick={() => setPage(page + 1)} disabled={page >= totalPages} className="btn-secondary px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50">
            Próxima
          </button>
        </div>
      </div>
    </div>
  );
}

export default TableControls;
