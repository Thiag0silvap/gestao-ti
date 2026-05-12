import api from '../api/api';

/**
 * Busca os logs de auditoria com filtros e paginação
 */
export const getAuditLogs = async (params = {}) => {
    try {
        const response = await api.get('/audit/logs', { params });
        return response.data;
    } catch (error) {
        console.error("Erro ao buscar logs de auditoria:", error);
        throw error;
    }
};
