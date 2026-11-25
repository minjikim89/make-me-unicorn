const required = (name) => {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is not set`);
  return value;
};

export const JWT_SECRET = required("JWT_SECRET");
export const JWT_SECRET_ENV_NAME = "JWT_SECRET";
export const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS ?? "https://app.shipyard.example").split(",");
