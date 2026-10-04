import config from "@hermi/eslint-config";

export default [...config, { ignores: ["apps/api/**", "apps/worker/**", ".reference/**", ".autopilot/**"] }];
