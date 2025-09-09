import React, { useRef, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FaTimes, FaInfoCircle, FaCube, FaCodeBranch } from "react-icons/fa";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/contexts/ThemeContext";
import { api } from "@/http/queryClient";
import axios from "@/http/axiosAgentConfig";


export default function HelpPanel({ isOpen, onClose }: any) {
  const panelRef = useRef<HTMLDivElement>(null);
  const { primaryHex } = useTheme();
  
  const uiVersion = import.meta.env.VITE_MODULE_VERSION || "NOT ENV";
  const [modules, setModules] = useState([
    { name: "Dataflow", version: "n/a" },
    { name: "MultiAgent", version: "n/a" },
    { name: "UI", version: uiVersion },
    { name: "SSO", version: "n/a" },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch versions
  useEffect(() => {
    const fetchVersions = async () => {
      setLoading(true);
      try {
        const updatedModules = await Promise.all(
          modules.map(async (module) => {
            try {
              let res;
  
              if (module.name === "Dataflow") {
                res = await api.get("/health/version");
              } else if (module.name === "MultiAgent") {
                res = await axios.get("/health/version");
              } else if (module.name === "SSO") {
                res = await api.get("/health/version");
              }
  
              // If response exists and is valid → return updated version
              if (res && res.data.module_version !== "unknown") {
                return { ...module, version: res.data.module_version };
              }
  
              // If response exists but version is unknown → set to "N/A"
              return { ...module, version: "N/A" };
  
            } catch (error) {
              console.error(`Failed to fetch version for ${module.name}`, error);
              return { ...module, version: "N/A" };
            }
          })
        );
  
        // Update the state **after** all requests finish
        setModules(updatedModules);
      } catch (err) {
        console.error(err);
        setError("Failed to fetch module versions");
      } finally {
        setLoading(false);
      }
    };
  
    if (isOpen) fetchVersions();
  }, [isOpen]);

  if (!isOpen) return null;

  const backgroundDark = "#121722"; // Panel background
  const moduleBg = "#1a2332"; // Module card background

  return (
    <AnimatePresence>
      <motion.div
        ref={panelRef}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.2 }}
        className="absolute top-full right-0 z-50 mt-2 w-96 border rounded-lg shadow-2xl overflow-hidden"
        style={{ backgroundColor: backgroundDark, borderColor: "#2a3441" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between p-4 border-b rounded-t-lg"
          style={{ backgroundColor: backgroundDark, borderColor: "#2a3441" }}
        >
          <div className="flex items-center gap-2">
            <FaInfoCircle className="text-white w-5 h-5" />
            <h2 className="text-lg font-semibold text-white">Modules & Versions</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-full hover:bg-white/20 text-white transition-colors"
          >
            <FaTimes />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 max-h-80 overflow-y-auto">
          {loading ? (
            <div className="text-center text-gray-400">Loading...</div>
          ) : error ? (
            <div className="text-center text-red-500">{error}</div>
          ) : modules.length === 0 ? (
            <div className="text-center text-gray-400">No modules found</div>
          ) : (
            <div className="space-y-3">
              {modules.map((module, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 border rounded-lg"
                  style={{ backgroundColor: moduleBg, borderColor: "#2a3441" }}
                >
                  <div className="flex items-center gap-3">
                    <FaCube className="text-white w-5 h-5" />
                    <span className="text-white font-medium">{module.name}</span>
                  </div>
                  <Badge
                    variant="secondary"
                    className="flex items-center gap-1"
                    style={{ backgroundColor: primaryHex || "#3b82f6", color: "#fff" }}
                  >
                    <FaCodeBranch className="w-3 h-3" /> {module.version}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
