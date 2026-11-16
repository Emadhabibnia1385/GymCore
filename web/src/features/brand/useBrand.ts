import { useQuery } from "@tanstack/react-query";
import { brandQuery, DEFAULT_BRAND, type Brand } from "./api";

export function useBrand(): Brand {
	return useQuery(brandQuery).data ?? DEFAULT_BRAND;
}
