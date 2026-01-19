import { api1Handlers } from "./api1.handlers";
import { api2Handlers } from "./api2.handlers";
import { api3Handlers } from "./api3.handlers";

export const handlers = [...api1Handlers, ...api2Handlers, ...api3Handlers];

