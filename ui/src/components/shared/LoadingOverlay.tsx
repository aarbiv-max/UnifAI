import ReactLoading from "react-loading";

interface LoadingProps {
    text: string;
}

export const LoadingOverlay: React.FC<LoadingProps> = ({text}) => (
  <div className="loading-overlay">
    <ReactLoading type="bubbles" color="#000" height={100} width={100} />
    <h2 style={{ marginTop: '20px', fontSize: '1.5em', textAlign: 'center', color: '#000' }}>
      {text}
    </h2>
  </div>
);