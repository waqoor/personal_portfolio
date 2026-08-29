export * from "./client";
export * from "./schemas";
export * from "./public-api";
export * from "./admin-api";

import { AdminApi } from "./admin-api";
import { HttpClient, type ApiClientConfig } from "./client";
import { PublicApi } from "./public-api";

export type PortfolioApi = ReturnType<typeof createPortfolioApi>;

export function createPortfolioApi(config: ApiClientConfig) {
  const http = new HttpClient(config);
  return {
    public: new PublicApi(http),
    admin: new AdminApi(http),
  } as const;
}
