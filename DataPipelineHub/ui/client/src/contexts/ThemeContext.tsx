import React, { createContext, useState, useContext, useEffect } from "react";

type Theme = "dark" | "light";

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Default to dark mode, but check localStorage for saved preference
  const [theme, setTheme] = useState<Theme>(() => {
    const savedTheme = localStorage.getItem("theme");
    return (savedTheme as Theme) || "dark";
  });

  // Update body and html classes when theme changes
  useEffect(() => {
    const root = document.documentElement;
    const body = document.body;
    
    // Remove old classes
    root.classList.remove("dark", "light");
    body.classList.remove("light-mode", "dark-mode");
    
    // Add new classes - both Tailwind's expected 'dark' class and custom classes for CSS variables
    if (theme === "dark") {
      root.classList.add("dark");
      body.classList.add("dark-mode");
    } else {
      root.classList.add("light");
      body.classList.add("light-mode");
    }
    
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
