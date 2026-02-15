import { ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import GlassPanel from "@/components/ui/GlassPanel";

interface AnalyticCardProps {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function AnalyticCard({ title, icon, children, className }: AnalyticCardProps) {
  return (
    <GlassPanel>
      <Card className={`shadow-card border-gray-800 h-full flex flex-col bg-transparent border-0 ${className || ''}`}>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-heading flex items-center gap-2">
            {icon}
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {children}
        </CardContent>
      </Card>
    </GlassPanel>
  );
}

