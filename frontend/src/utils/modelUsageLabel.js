export function isNonBillableModel(_modelUsed) {
  return false;
}

export function formatModelUsageLine(modelUsed) {
  if (!modelUsed) return '';
  return `Model: ${modelUsed}`;
}
