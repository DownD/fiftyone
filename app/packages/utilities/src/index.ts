import _ from "lodash";

export const toCamelCase = (obj: object): object =>
  _.transform(obj, (acc, value, key, target) => {
    const camelKey = _.isArray(target) ? key : _.camelCase(key);

    acc[
      `${typeof key === "string" && key.startsWith("_") ? "_" : ""}${camelKey}`
    ] = _.isObject(value) ? toCamelCase(value) : value;
  });

export const toSnakeCase = (obj: object): object =>
  _.transform(obj, (acc, value, key, target) => {
    const snakeKey = _.isArray(target) ? key : _.snakeCase(key);

    acc[snakeKey] = _.isObject(value) ? toSnakeCase(value) : value;
  });

export const move = <T>(
  array: Array<T>,
  moveIndex: number,
  toIndex: number
): Array<T> => {
  const item = array[moveIndex];
  const length = array.length;
  const diff = moveIndex - toIndex;

  if (diff > 0) {
    // move left
    return [
      ...array.slice(0, toIndex),
      item,
      ...array.slice(toIndex, moveIndex),
      ...array.slice(moveIndex + 1, length),
    ];
  } else if (diff < 0) {
    // move right
    const targetIndex = toIndex + 1;
    return [
      ...array.slice(0, moveIndex),
      ...array.slice(moveIndex + 1, targetIndex),
      item,
      ...array.slice(targetIndex, length),
    ];
  }
  return array;
};

type KeyValue<T> = {
  [key: string]: T;
};

export const removeKeys = <T>(
  obj: KeyValue<T>,
  keys: Iterable<string>,
  startsWith: boolean = false
): KeyValue<T> => {
  const set = new Set(keys);
  const values = Array.from(keys);

  return Object.fromEntries(
    Object.entries(obj).filter(
      startsWith
        ? ([key]) => values.every((k) => !key.startsWith(k))
        : ([key]) => !set.has(key)
    )
  );
};
