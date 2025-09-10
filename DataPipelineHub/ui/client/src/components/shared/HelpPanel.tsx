import React, { useRef, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaTimes,
  FaInfoCircle,
  FaCube,
  FaCodeBranch,
  FaSyncAlt,
  FaCheck,
} from "react-icons/fa";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/contexts/ThemeContext";
import { api } from "@/http/queryClient";
import { api as apiAuth } from '@/http/authClient';
import axios from "@/http/axiosAgentConfig";

export default function HelpPanel({ isOpen, onClose }: any) {
  const panelRef = useRef<HTMLDivElement>(null);
  const { primaryHex } = useTheme();

  const uiVersion = "%%VERSION%%" || "N/A";
  const [modules, setModules] = useState([
    { name: "Dataflow", version: "n/a" },
    { name: "MultiAgent", version: "n/a" },
    { name: "UI", version: uiVersion },
    { name: "SSO", version: "n/a" },
  ]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Fetch versions
  const fetchVersions = async () => {
    setLoading(true);
    try {
      const updatedModules = await Promise.all(
        modules.map(async (module) => {
          if (module.name === "UI") return module;
          try {
            let res;

            if (module.name === "Dataflow") {
              res = await api.get("/health/version");
            } else if (module.name === "MultiAgent") {
              res = await axios.get("/health/version");
            } else if (module.name === "SSO") {
              res = await apiAuth.get("/health/version");
            }

            if (res && res.data.module_version !== "unknown") {
              return { ...module, version: res.data.module_version };
            }

            return { ...module, version: "N/A" };
          } catch (error) {
            console.error(`Failed to fetch version for ${module.name}`, error);
            return { ...module, version: "N/A" };
          }
        })
      );

      setModules(updatedModules);
    } catch (err) {
      console.error(err);
      setError("Failed to fetch module versions");
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh every 10 seconds **only when panel is open**
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;

    if (isOpen) {
      fetchVersions();
      interval = setInterval(() => {
        fetchVersions();
      }, 10000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isOpen]);

  // Copy version to clipboard
  const handleCopy = async (version: string, index: number) => {
    try {
      await navigator.clipboard.writeText(version);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

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
          className="flex items-center justify-between p-3 border-b rounded-t-lg"
          style={{ backgroundColor: backgroundDark, borderColor: "#2a3441" }}
        >
          <div className="flex items-center gap-2">
            <FaInfoCircle className="text-white w-5 h-5" />
            <h2 className="text-lg font-semibold text-white">Module Version Overview</h2>
          </div>
          <div className="flex items-center gap-2">
            {/* Refresh Button */}
            <button
              onClick={fetchVersions}
              className="p-1 rounded-full hover:bg-white/20 text-white transition-colors"
              title="Refresh"
            >
              <FaSyncAlt className={loading ? "animate-spin" : ""} />
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded-full hover:bg-white/20 text-white transition-colors"
            >
              <FaTimes />
            </button>
          </div>
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
            <div className="space-y-1.5">
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
                    onClick={() => handleCopy(module.version, index)}
                    className="flex items-center gap-1 cursor-pointer hover:scale-105 transition-transform shadow-sm"
                    style={{
                      backgroundColor: primaryHex || "#3b82f6",
                      color: "#fff",
                      borderRadius: "8px", // 🔹 Make it more square instead of round
                      padding: "2px 10px", // 🔹 Slightly better spacing for text
                      fontWeight: 500,
                      fontSize: "0.85rem",
                    }}
                    title="Click to copy version"
                  >
                    {copiedIndex === index ? (
                      <FaCheck className="w-3 h-3 text-green-300" />
                    ) : (
                      <FaCodeBranch className="w-3 h-3" />
                    )}
                    {module.version}
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
