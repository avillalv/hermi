import { QueryClient } from "@tanstack/react-query"

/** The one query cache. Sign-out clears it so the next person never sees the last person's data. */
export const queryClient = new QueryClient()
