const API = import.meta.env.VITE_API_URL;

export async function login(email: string, password: string) {
  const res = await fetch(`${API}/auth/login`, { method: "POST", body: JSON.stringify({ email, password }) });
  const { token } = await res.json();
  localStorage.setItem("token", token);
  localStorage.setItem("theme", "dark");
}
