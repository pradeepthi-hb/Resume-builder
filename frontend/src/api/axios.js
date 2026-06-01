import axios from "axios";
import { getToken } from "../auth/AuthContext"; 

export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:5000/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = getToken(); 
  if (token) {
    config.headers.Authorization = `Bearer ${token}`; 
  }
  return config;
});

export default api;
