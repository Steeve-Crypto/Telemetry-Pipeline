import { DeviceDetailPage } from "@/components/devices/device-detail-page";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function DeviceDetailRoute({ params }: PageProps) {
  const { id } = await params;
  return <DeviceDetailPage deviceId={decodeURIComponent(id)} />;
}