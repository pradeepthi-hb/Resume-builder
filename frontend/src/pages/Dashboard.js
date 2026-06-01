import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";
import "../components/Dashboard.css";
import { toast } from "react-toastify";


function Dashboard() {
  const [resumes, setResumes] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/resumes")
      .then(res => setResumes(res.data))
      .catch(err => console.log(err));
  }, []);

  const handleDelete = (id) => {
    api.delete(`/resume/${id}`)
      .then(() => {
        setResumes(resumes.filter(r => r.id !== id));
        toast.success("Resume deleted successfully!");
      })
      .catch(err => console.log(err));
  };



  return (
  <div className="dashboard-container">
    <div className="dashboard-header">
      <h2>Your Resumes</h2>
      <button
        className="create-btn"
        onClick={() => navigate("/resume/new")}
      >
        + Create New Resume
      </button>
    </div>

    <div className="resume-grid">
      {resumes.map(resume => (
        <div key={resume.id} className="resume-card">

          {/* Preview Thumbnail */}

          <div className="resume-thumbnail">
            <div className="iframe-container">
              <iframe
                srcDoc={resume.resume_html}
                title={`resume-${resume.id}`}
                className="resume-iframe"
              />
            </div>
          </div>


          <div className="resume-info">
            <h3>Resume #{resume.id}</h3>
            <p>Template: {resume.template}</p>
            {/* {resume.source_type === "imported" ? (
              <p>
                Source: Imported
                {typeof resume.parser_confidence === "number"
                  ? ` (${Math.round(resume.parser_confidence * 100)}% parser confidence)`
                  : ""}
              </p>
            ) : (
              <p>Source: Manual</p>
            )} */}

            <div className="resume-actions">
              <button
                className="edit-btn"
                onClick={() => navigate(`/resume/${resume.id}`)}
              >
                Edit
              </button>
 
              <button
                className="delete-btn"
                onClick={() => handleDelete(resume.id)}
              >
                Delete
              </button>
            </div>
          </div>

        </div>
      ))}
    </div>
  </div>
);

}

export default Dashboard;
