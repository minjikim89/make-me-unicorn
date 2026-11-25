import { throttle } from "lodash";

// "express" delivery and "expression" are words, not frameworks.
export const onScroll = throttle(() => {}, 200);

export function UpdateBanner({ version }: { version: string }) {
  return <p>{`Update available: ${version}. Select a plan from the list.`}</p>;
}
