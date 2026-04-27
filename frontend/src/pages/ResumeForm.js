import React, { useState, useEffect, useRef, useCallback } from "react";
import "../components/ResumeForm.css";
import "../components/analytics.css";
import api from "../api/axios";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { toast } from "react-toastify";


const steps = [
  "Personal",
  "Templates",
  "Education",
  "Experience",
  "Skills",
  "Projects",
  "Certifications & Achievements",
  "Languages",
  "Summary",
];

const EMPTY_FORM = {
  personal: {
    firstName: "",
    lastName: "",
    profession: "",
    onet_code: "",       
    city: "",
    country: "",
    pincode: "",
    phone: "",
    email: "",
    linkedin: "",
    websites: []
  },
  summary: "",
  skills: [],
  education: [],
  experience: [],
  projects: [],
  certifications: [],
  languages: [],
  template: "classic"
};


const MonthSelect = ({ value, onChange, disabled }) => (
  <select value={value} onChange={onChange} disabled={disabled}>
    <option value="">Month</option>
    {["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].map(m => (
      <option key={m}>{m}</option>
    ))}
  </select>
);

const YearSelect = ({ value, onChange, startYear = 2026, count = 30, disabled }) => (
  <select value={value} onChange={onChange} disabled={disabled}>
    <option value="">Year</option>
    {Array.from({ length: count }, (_, i) => (
      <option key={i}>{startYear - i}</option>
    ))}
  </select>
);

function ResumeForm() {

  const [formData, setFormData] = useState(EMPTY_FORM);

  const saveTimeout = useRef(null);

  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [expSuggestions, setExpSuggestions] = useState({});
  const [activeExpDropdown, setActiveExpDropdown] = useState(null);
  const [suggestedSkills, setSuggestedSkills] = useState([]);

  const [skillOnetCode, setSkillOnetCode] = useState(null);
  const [skillJobInput, setSkillJobInput] = useState("");
  const [skillSuggestions, setSkillSuggestions] = useState([]);
  const [showSkillDropdown, setShowSkillDropdown] = useState(false);

  const [matchOutdated, setMatchOutdated] = useState(false);
  const [lastMatchInput, setLastMatchInput] = useState(null);

  const [analytics, setAnalytics] = useState({
      resume_score: 0,
      completeness_score: 0,
      action_verbs_used: 0,
      keywords_count: 0,
      quantified_achievements: 0,
      word_count: 0,
      estimated_pages: 0,
      skills_count: 0,
      experience_entries: 0,
      bullet_points: 0,
      has_email: false,
      has_phone: false,
      has_linkedin: false,
      keywords_found: [],
      missing_sections: [],
      suggestions: [],
      ats_score: 0,
      keyword_alignment:0
  });
  const [showAnalytics, setShowAnalytics] = useState(false);

  const [showJobMatch, setShowJobMatch] = useState(false);
  const [jobText, setJobText] = useState("");
  const [jobMatch, setJobMatch] = useState(null);

  const professionDebounceRef = useRef(null);
  const expDebounceRef = useRef(null);

  const { id: routeId } = useParams();
  const [id, setId] = useState(routeId || null);
  const [variation, setVariation] = useState(0);

  const [step, setStep] = useState(0);
  const totalSteps = 8;

  const nextStep = () => {
    if (step < totalSteps) setStep(step + 1);
  };

  const prevStep = () => {
    if (step > 0) setStep(step - 1);
  };

  const navigate = useNavigate();
  const location = useLocation();
  const isLoaded = useRef(false);
  const [previewHTML, setPreviewHTML] = useState("");
  const [integrationSession, setIntegrationSession] = useState(null);
  const [integrationReady, setIntegrationReady] = useState(false);

  const searchParams = new URLSearchParams(location.search);
  const isIntegrationMode = location.pathname.startsWith("/integrations/hireyo");
  const integrationToken = searchParams.get("token") || "";
  const integrationCandidateName = searchParams.get("candidate_name") || integrationSession?.candidate_name || "";
  const integrationReturnUrl = integrationSession?.return_url || searchParams.get("return_url") || "";

  const saveIntegrationDraft = useCallback((payload) => {
    return api.put("/integrations/hireyo/draft", {
      token: integrationToken,
      ...payload,
    });
  }, [integrationToken]);

  useEffect(() => {
    if (!isIntegrationMode) {
      setIntegrationReady(true);
      setIntegrationSession(null);
      return;
    }

    if (!integrationToken) {
      setIntegrationReady(false);
      toast.error("Missing Hireyo launch token.");
      return;
    }

    setIntegrationReady(false);

    api.get(`/integrations/hireyo/session${location.search}`)
      .then((res) => {
        const data = res.data;
        setIntegrationSession(data);
        isLoaded.current = false;
        setFormData(data.draft ?? EMPTY_FORM);
        setPreviewHTML(data.resume_html ?? "");
        setAnalytics(data.analytics ?? {
          resume_score: 0,
          completeness_score: 0,
          action_verbs_used: 0,
          keywords_count: 0,
          quantified_achievements: 0,
          word_count: 0,
          estimated_pages: 0,
          skills_count: 0,
          experience_entries: 0,
          bullet_points: 0,
          has_email: false,
          has_phone: false,
          has_linkedin: false,
          keywords_found: [],
          missing_sections: [],
          suggestions: [],
          ats_score: 0,
          keyword_alignment: 0
        });
        isLoaded.current = true;
        setIntegrationReady(true);
      })
      .catch((err) => {
        console.error(err);
        setIntegrationReady(false);
        toast.error(err?.response?.data?.error || "Unable to initialize Hireyo integration.");
      });
  }, [integrationToken, isIntegrationMode, location.search]);

  // ── Personal ─────────────────────────────────────────────────────────────
  const handlePersonalChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      personal: { ...prev.personal, [name]: value }
    }));

    if (name === "profession") {
      clearTimeout(professionDebounceRef.current);
      if (value.length >= 2) {
        professionDebounceRef.current = setTimeout(() => {
          fetchSuggestions(value);
        }, 300);
      } else {
        setSuggestions([]);
        setShowDropdown(false);
      }
    }
  };

  const fetchSuggestions = async (query) => {
    try {
      const res = await fetch(
        `http://localhost:5000/api/occupations/search?q=${encodeURIComponent(query)}`
      );
      const data = await res.json();
      setSuggestions(data);
      setShowDropdown(true);
    } catch (err) {
      console.error("Error fetching professions:", err);
    }
  };

  const addWebsite = () => {
    setFormData(prev => ({
      ...prev,
      personal: { ...prev.personal, websites: [...prev.personal.websites, ""] }
    }));
  };

  const updateWebsite = (index, value) => {
    setFormData(prev => {
      const updated = [...prev.personal.websites];
      updated[index] = value;
      return { ...prev, personal: { ...prev.personal, websites: updated } };
    });
  };

  const removeWebsite = (index) => {
    setFormData(prev => ({
      ...prev,
      personal: {
        ...prev.personal,
        websites: prev.personal.websites.filter((_, i) => i !== index)
      }
    }));
  };

  // ── Summary ───────────────────────────────────────────────────────────────
  const updateSummary = (value) => {
    setFormData(prev => ({ ...prev, summary: value }));
  };

  // ── Skills ────────────────────────────────────────────────────────────────
  const addSkill = () => {
    setFormData(prev => ({ ...prev, skills: [...prev.skills, ""] }));
  };

  const updateSkill = (index, value) => {
    setFormData(prev => {
      const updated = [...prev.skills];
      updated[index] = value;
      return { ...prev, skills: updated };
    });
  };

  const removeSkill = (index) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.filter((_, i) => i !== index)
    }));
  };

  useEffect(() => {
    if (!skillOnetCode) {
      setSuggestedSkills([]);
      return;
    }
    const fetchSkills = async () => {
      try {
        const res = await fetch(`http://localhost:5000/api/occupations/skills/${skillOnetCode}`);
        const data = await res.json();
        setSuggestedSkills(data.map(item => item.technology));
      } catch (err) {
        console.error("Error fetching skills:", err);
      }
    };
    fetchSkills();
  }, [skillOnetCode]);

  useEffect(() => {
    if (!skillJobInput) {
      setSkillOnetCode(formData.personal?.onet_code || null);
    }
  }, [formData.personal?.onet_code, skillJobInput]); 

  // ── Education ─────────────────────────────────────────────────────────────
  const addEducation = () => {
    setFormData(prev => ({
      ...prev,
      education: [
        ...prev.education,
        {
          school: "",
          location: "",
          field: "",
          degree: "",
          gradMonth: "",
          gradYear: "",
          gpa: ""
        }
      ]
    }));
  };

  const updateEducation = (index, field, value) => {
    setFormData(prev => {
      const updated = [...prev.education];
      updated[index] = { ...updated[index], [field]: value };
      return { ...prev, education: updated };
    });
  };

  const removeEducation = (index) => {
    setFormData(prev => ({
      ...prev,
      education: prev.education.filter((_, i) => i !== index)
    }));
  };

  // ── Experience ────────────────────────────────────────────────────────────
  const addExperience = () => {
    setFormData(prev => ({
      ...prev,
      experience: [
        ...prev.experience,
        {
          title: "",
          employer: "",
          location: "",
          description: "",
          startMonth: "",
          startYear: "",
          endMonth: "",
          endYear: "",
          current: false
        }
      ]
    }));
  };


  const fetchExperienceSuggestions = useCallback((query, index) => {
    clearTimeout(expDebounceRef.current);
    expDebounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(
          `http://localhost:5000/api/occupations/search?q=${encodeURIComponent(query)}`
        );
        const data = await res.json();
        setExpSuggestions(prev => ({ ...prev, [index]: data }));
        setActiveExpDropdown(index);
      } catch (err) {
        console.error("Error fetching occupations:", err);
      }
    }, 300);
  }, []);

  const updateExperience = (index, field, value) => {
    setFormData(prev => {
      const updated = [...prev.experience];
      updated[index] = { ...updated[index], [field]: value };

      if (field === "description") {
        updated[index].originalDescription = value;
        if (!updated[index].originalDescription) {
        updated[index].originalDescription = value;
      }
      }

      if (field === "current" && value === true) {
        updated[index].endMonth = "";
        updated[index].endYear = "";
      }

      return { ...prev, experience: updated };
    });
  };

  const removeExperience = (index) => {
    setFormData(prev => ({
      ...prev,
      experience: prev.experience.filter((_, i) => i !== index)
    }));
  };

  // ── Projects ──────────────────────────────────────────────────────────────
  const addProject = () => {
    setFormData(prev => ({
      ...prev,
      projects: [
        ...prev.projects,
        { title: "", description: "", role: "", tools: "", url: "" }
      ]
    }));
  };

  const updateProject = (index, field, value) => {
    setFormData(prev => {
      const updated = [...prev.projects];
      updated[index] = { ...updated[index], [field]: value };
      return { ...prev, projects: updated };
    });
  };

  const removeProject = (index) => {
    setFormData(prev => ({
      ...prev,
      projects: prev.projects.filter((_, i) => i !== index)
    }));
  };

  // ── Certifications ────────────────────────────────────────────────────────
  const addCertification = () => {
    setFormData(prev => ({
      ...prev,
      certifications: [
        ...prev.certifications,
        { name: "", issuingOrg: "", achievedDate: "", url: "" }
      ]
    }));
  };

  const updateCertification = (index, field, value) => {
    setFormData(prev => {
      const updated = [...prev.certifications];
      updated[index] = { ...updated[index], [field]: value };
      return { ...prev, certifications: updated };
    });
  };

  const removeCertification = (index) => {
    setFormData(prev => ({
      ...prev,
      certifications: prev.certifications.filter((_, i) => i !== index)
    }));
  };

  // ── Languages ─────────────────────────────────────────────────────────────
  const addLanguage = () => {
    setFormData(prev => ({
      ...prev,
      languages: [...prev.languages, { name: "", level: "Beginner" }]
    }));
  };

  const updateLanguage = (index, field, value) => {
    setFormData(prev => {
      const updated = [...prev.languages];
      updated[index] = { ...updated[index], [field]: value };
      return { ...prev, languages: updated };
    });
  };

  const removeLanguage = (index) => {
    setFormData(prev => ({
      ...prev,
      languages: prev.languages.filter((_, i) => i !== index)
    }));
  };

  // ── Auto-save ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isLoaded.current) {
      isLoaded.current = true;
      return;
    }

    if (isIntegrationMode && (!integrationReady || !integrationToken)) {
      return;
    }
    
    saveTimeout.current = setTimeout(() => {
      const payload = cleanFormData(formData);

      if (isIntegrationMode) {
        saveIntegrationDraft(payload)
          .then(res => {
            setPreviewHTML(res.data.resume_html);
            setAnalytics(res.data.analytics);
            setMatchOutdated(true);
          })
          .catch(err => console.log(err));
      } else if (id) {
        api.put(`/resume/${id}`, payload)
          .then(res => {
            setPreviewHTML(res.data.resume_html);
            setAnalytics(res.data.analytics);
            setMatchOutdated(true);
          })
          .catch(err => console.log(err));
      } else {
        api.post("/resume", payload)
          .then(res => {
            setId(res.data.resume_id);
            setPreviewHTML(res.data.resume_html);
            setAnalytics(res.data.analytics);
            navigate(`/resume/${res.data.resume_id}`);
          })
          .catch(err => console.log(err));
      }
    }, 1000);

    return () => clearTimeout(saveTimeout.current);
  }, [formData, id, integrationReady, integrationToken, isIntegrationMode, navigate, saveIntegrationDraft]);

  // ── Load resume ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (isIntegrationMode) {
      return;
    }

    if (id) {
      api.get(`/resume/${id}`)
        .then(res => {
          const data = res.data;
          isLoaded.current = false;
          setFormData({
            personal:       data.personal       ?? EMPTY_FORM.personal,
            summary:        data.summary        ?? "",
            skills:         data.skills         ?? [],
            education:      data.education      ?? [],
            experience:     data.experience     ?? [],
            projects:       data.projects       ?? [],
            certifications: data.certifications ?? [],
            languages:      data.languages      ?? [],
            template:       data.template       ?? "classic"
          });
          if (data.resume_html) setPreviewHTML(data.resume_html);
          isLoaded.current = true;
        })
        .catch(err => console.log(err));
    } else {
      isLoaded.current = true;
    }
  }, [id, isIntegrationMode]);

  // ── Check empty ───────────────────────────────────────────────────────────
  const isFormCompletelyEmpty = () => {
    const { personal, summary, skills, education, experience, projects, certifications, languages } = formData;

    const personalEmpty = Object.entries(personal).every(([key, value]) => {
      if (key === "onet_code") return true; // internal field, ignore
      if (Array.isArray(value)) return value.length === 0;
      return !value;
    });

    return (
      personalEmpty &&
      !summary &&
      skills.length === 0 &&
      education.length === 0 &&
      experience.length === 0 &&
      projects.length === 0 &&
      certifications.length === 0 &&
      languages.length === 0
    );
  };

  // ── Clean formData ────────────────────────────────────────────────────────
  const cleanFormData = (data) => {
    const cleaned = JSON.parse(JSON.stringify(data));

    cleaned.personal.websites = cleaned.personal.websites
      .map(site => site.trim())
      .filter(site => site !== "");

    cleaned.skills = cleaned.skills
      .map(skill => skill.trim())
      .filter(skill => skill !== "");

    cleaned.education = cleaned.education.filter(edu =>
      edu.school?.trim() !== "" ||
      edu.degree?.trim() !== "" ||
      edu.field?.trim() !== ""
    );

    cleaned.experience = cleaned.experience.filter(exp =>
      exp.title?.trim() !== "" ||
      exp.employer?.trim() !== "" ||
      exp.description?.trim() !== ""
    );

    cleaned.projects = cleaned.projects.filter(proj =>
      proj.title?.trim() !== "" ||
      proj.description?.trim() !== ""
    );

    cleaned.certifications = cleaned.certifications.filter(cert =>
      cert.name?.trim() !== ""
    );

    cleaned.languages = cleaned.languages.filter(lang =>
      lang.name?.trim() !== ""
    );

    cleaned.summary = cleaned.summary.trim();

    return cleaned;
  };

  const handleGenerateSummary = async () => {
    const toastId = toast.loading("Generating summary...");

    try {
      const response = await fetch("http://localhost:5000/api/ai/generate-summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resumeData: cleanFormData(formData),
          variation: variation
        })
      });
      

      const data = await response.json();
      setFormData(prev => ({ ...prev, summary: data.summary }));
      setVariation(prev => (prev + 1) % 10);
      toast.update(toastId, {
          render: "Summary generated!",
          type: "success",
          isLoading: false,
          autoClose: 2000
      });
    } catch (err) {
      console.error("Error generating summary:", err);
      toast.error("Failed to generate summary. Please try again.");
    }
  };

  const handleEnhance = async (index) => {
    const toastId = toast.loading("Enhancing experience...");
    try {
      const res = await api.post("/ai/enhance-experience", {
        resumeData: cleanFormData(formData),
        index: index
      });

      setFormData(prev => {
        const updated = [...prev.experience];
        updated[index] = {
          ...updated[index],
          description: res.data.experience[index]?.description ?? updated[index].description
        };
        return { ...prev, experience: updated };
      });
   
      if (!res.data.experience[index]?.description) {
        toast.update(toastId, {
          render: "Please provide a description to enhance.",
          type: "warning",
          isLoading: false,
          autoClose: 3000
        });
      } else {
        toast.update(toastId, {
          render: "Experience enhanced!",
          type: "success",
          isLoading: false,
          autoClose: 2000
      });
      }
    } catch (err) {
      console.error("Enhance failed:", err);
      toast.update(toastId, {
        render: "Failed to enhance. Please try again.",
        type: "error",
        isLoading: false,
        autoClose: 3000
      });
    }
  };
  

  const handleResetExperience = (index) => {
    const updatedExperience = [...formData.experience];

    if (updatedExperience[index].originalDescription) {
      updatedExperience[index].description =
        updatedExperience[index].originalDescription;
    }

    setFormData({
      ...formData,
      experience: updatedExperience,
    });
  };
  // ── Submit ────────────────────────────────────────────────────────────────
  function handleSubmit() {
    if (isFormCompletelyEmpty()) {
      toast.error("Cannot submit an empty resume.");
      return;
    }

    const payload = cleanFormData(formData);

    if (isIntegrationMode) {
      const toastId = toast.loading("Sending resume to Hireyo...");

      saveIntegrationDraft(payload)
        .then((saveRes) => {
          setPreviewHTML(saveRes.data.resume_html);
          setAnalytics(saveRes.data.analytics);

          return api.post("/integrations/hireyo/submit", {
            token: integrationToken,
            resume_name: `${formData.personal.firstName || integrationCandidateName || "Candidate"} Resume`,
          });
        })
        .then((submitRes) => {
          toast.update(toastId, {
            render: "Resume sent to Hireyo successfully!",
            type: "success",
            isLoading: false,
            autoClose: 2500
          });

          const returnUrl = submitRes?.data?.return_url || integrationReturnUrl;
          if (returnUrl) {
            setTimeout(() => {
              window.location.href = returnUrl;
            }, 1000);
          }
        })
        .catch((err) => {
          console.error(err);
          toast.update(toastId, {
            render: err?.response?.data?.error || "Failed to send resume to Hireyo.",
            type: "error",
            isLoading: false,
            autoClose: 4000
          });
        });

      return;
    }

    if (id) {
      api.put(`/resume/${id}`, payload)
        .then(res => {
          setPreviewHTML(res.data.resume_html);
          toast.success("Resume saved successfully!");
        })
        .catch(err => console.log(err));
    } else {
      api.post("/resume", payload)
        .then(res => {
          toast.success("Resume created successfully!");
          setId(res.data.resume_id);
          setPreviewHTML(res.data.resume_html);
          navigate(`/resume/${res.data.resume_id}`);
        })
        .catch(err => console.log(err));
    }
  }

  // ── Print / Download ──────────────────────────────────────────────────────
  const handlePrint = async () => {
    if (isFormCompletelyEmpty()) {
      toast.error("Cannot download empty resume.");
      return;
    }

    if (!isIntegrationMode && !id) {
      toast.error("Please save your resume before downloading.");
      return;
    }

    const toastId = toast.loading("Preparing your resume PDF...");

    try {
      const response = await api.get(
        isIntegrationMode ? "/integrations/hireyo/download" : `/resume/${id}/download`,
        {
        params: isIntegrationMode ? { token: integrationToken } : undefined,
        responseType: "blob",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`
        }
      });

      const blob = new Blob([response.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "resume.pdf";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.update(toastId, {
        render: "Downloaded successfully!",
        type: "success",
        isLoading: false,
        autoClose: 3000
      });

    } catch (error) {
      console.error("Download failed:", error);
      toast.update(toastId, {
        render: "Download failed. Please try again.",
        type: "error",
        isLoading: false,
        autoClose: 3000
      });
    }
  };


  const handleDelete = (resumeId) => {
    api.delete(`/resume/${resumeId}`)
      .then(() => {
        toast.success("Resume deleted successfully!");
        navigate("/");
      })
      .catch(err => console.log(err));
  };

  const handleSkillJobChange = async (value) => {
    setSkillJobInput(value);

    if (!value) {
      setSkillSuggestions([]);
      setShowSkillDropdown(false);
      setSkillOnetCode(formData.personal?.onet_code || null);
      return;
    }

    if (value.length < 2) {
      setSkillSuggestions([]);
      setShowSkillDropdown(false);
      return;
    }

    setSkillOnetCode(null); 
    try {
      const res = await fetch(`http://localhost:5000/api/occupations/search?q=${encodeURIComponent(value)}`);
      const data = await res.json();
      setSkillSuggestions(data);
      setShowSkillDropdown(data.length > 0);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSkillSelect = (occupation) => {
    setSkillJobInput(occupation.title);
    setSkillOnetCode(occupation.onet_code);
    setShowSkillDropdown(false);
  };

  const handleJobMatch = async () => {
    const currentInput = { jobText, formData };
    if (jobText && formData){

      if (JSON.stringify(currentInput) === JSON.stringify(lastMatchInput)) {
        toast.info("Results already up to date.");
        return;
      }
      const res = await fetch(`http://localhost:5000/api/job-match`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          resume: formData,
          job_description: jobText
        })
      });

    const data = await res.json();
    setJobMatch(data);
    setLastMatchInput(currentInput);
    }
    else{
      toast.warning("Job Description is empty");
      return
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="resume-builder">
      <div className="form-section">
        <div className="form-header">
          <div>
            <h2>{isIntegrationMode ? "Build Resume for Hireyo" : "Resume Form"}</h2>
            {isIntegrationMode && integrationCandidateName ? (
              <p style={{ marginTop: "6px", color: "#64748B" }}>
                Creating a resume for {integrationCandidateName}
              </p>
            ) : null}
          </div>

          <div className="header-actions">
            <button
              type="button"
              className="change-template-btn"
              onClick={() => setStep(1)}
            >
              Change Template
            </button>

            <button
              type="button"
              className="print-btn"
              onClick={handlePrint}
            >
              Download
            </button>

            <button
              type="submit"
              className="submit-btn"
              onClick={handleSubmit}
            >
              {isIntegrationMode ? "Send to Hireyo" : "Submit"}
            </button>

            {!isIntegrationMode && id ? (
              <button
                className="delete-btn"
                onClick={() => handleDelete(id)}
              >
                Delete
              </button>
            ) : null}
          </div>
        </div>


        {/* ── Personal Details ── */}
        {step === 0 && (
          <div className="section">
          <div className="form-card">
          <h2>Personal Details</h2>
          <div className="input-row">
          <div className="input-group">
          <label htmlFor="firstname">First Name *</label>
          <input id="firstname" type="text" name="firstName" placeholder="Priya" maxLength={50}
            value={formData.personal.firstName} onChange={handlePersonalChange} required />
          </div>

          <div className="input-group">
          <label htmlFor="lastname">Last Name *</label>
          <input id="lastname" type="text" name="lastName" placeholder="Sharma" maxLength={50}
            value={formData.personal.lastName} onChange={handlePersonalChange} required />
          </div>
          </div>

          <div style={{ position: "relative" }}>
          <label htmlFor="profession">Profession</label>
          <input
            id="profession"
            type="text"
            name="profession"
            placeholder="Software Engineer"
            maxLength={40}
            value={formData.personal.profession}
            onChange={handlePersonalChange}
            onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
          />

            {showDropdown && suggestions.length > 0 && (
              <ul className="dropdown">
                {suggestions.map((item, index) => (
                  <li
                    key={index}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => {
                      setFormData(prev => ({
                        ...prev,
                        personal: {
                          ...prev.personal,
                          profession: item.title,
                          onet_code: item.onet_code  
                        }
                      }));
                      setShowDropdown(false);
                    }}
                  >
                    {item.title}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="input-row">
            <div className="input-group">
          <label htmlFor="city">City</label>
          <input id="city" type="text" name="city" placeholder="Bangalore" maxLength={30}
            value={formData.personal.city} onChange={handlePersonalChange} />
          </div>

          <div className="input-group">
          <label htmlFor="country">Country</label>
          <input id="country" type="text" name="country" placeholder="India" maxLength={30}
            value={formData.personal.country} onChange={handlePersonalChange} />
          </div>

          <div className="input-group">
          <label htmlFor="pincode">Pincode</label>
          <input id="pincode" type="text" name="pincode" placeholder="560034" maxLength={10}
            value={formData.personal.pincode} onChange={handlePersonalChange} />
          </div>
          </div>

          <div className="input-row">
          <div className="input-group">
          <label htmlFor="phone">Phone</label>
          <input id="phone" type="text" name="phone" placeholder="+91 91234 56789" maxLength={20}
            value={formData.personal.phone} onChange={handlePersonalChange} required />
          </div>

          <div className="input-group">
          <label htmlFor="email">Email *</label>
          <input id="email" type="email" name="email" placeholder="priya.sharma.dev@gmail.com" maxLength={50}
            value={formData.personal.email} onChange={handlePersonalChange} required />
          </div>
          </div>

          <label htmlFor="linkedin">LinkedIn Profile</label>
          <input id="linkedin" type="text" name="linkedin" placeholder="https://www.linkedin.com/in/priyasharma-tech" maxLength={100}
            value={formData.personal.linkedin} onChange={handlePersonalChange} />

          <hr />

          <h3>Additional Websites</h3>

          {formData.personal.websites.map((site, index) => (
            <div key={index} style={{ display: "flex", gap: "10px" }}>
              <input type="text" name="website" placeholder="Website (GitHub, Portfolio, etc.)" maxLength={100}
                value={site} onChange={(e) => updateWebsite(index, e.target.value)} />
              <button type="button" className="delete-icon-btn" onClick={() => removeWebsite(index)}>X</button>
            </div>
          ))}

          <button type="button" className="add-btn" onClick={addWebsite}>+ Add Website</button>

          </div>
          </div>
        )}

        {/* ── Professional Summary ── */}
        {step === 8 && (
        <div className="section">
          <div className="form-card">
          <h2>Professional Summary</h2>

          <textarea
            placeholder="Brief summary highlighting your experience, skills, and career goals"
            rows="5" style={{ width: "100%" }}
            value={formData.summary} name="summary" maxLength={700}
            onChange={(e) => updateSummary(e.target.value)}
          />
          <div style={{ textAlign: "right", fontSize: "0.85rem",
            color: (formData.summary?.length || 0) > 650 ? "#e63946" : "#666",
            fontWeight: (formData.summary?.length || 0) > 650 ? "bold" : "normal"
          }}>
            {(formData.summary?.length || 0)} / 700
          </div>
          <button type="button" className="gen-btn" onClick={handleGenerateSummary}>Generate with AI</button>

          </div>
        </div>
        )}

        {/* ── Education ── */}
        {step === 2 && (
        <div className="section">
          <div className="form-card">
        <h2>Education</h2>

        {formData.education.map((edu, index) => (
          <div key={index}>

            <label htmlFor={`education-school-${index}`}>School *</label>
            <input id={`education-school-${index}`} type="text" placeholder="St. Mary's College of Engineering" name="school" maxLength={80}
              value={edu.school} onChange={(e) => updateEducation(index, "school", e.target.value)} required />

            <label htmlFor={`education-location-${index}`}>Location</label>
            <input id={`education-location-${index}`} type="text" placeholder="Chennai, India" name="location" maxLength={50}
              value={edu.location} onChange={(e) => updateEducation(index, "location", e.target.value)} />

            <div className="input-row">
            <div className="input-group">
            <label htmlFor={`education-degree-${index}`}>Degree *</label>
            <input id={`education-degree-${index}`} type="text" placeholder="Bachelor of Technology (B.Tech)" name="degree" maxLength={50}
              value={edu.degree} onChange={(e) => updateEducation(index, "degree", e.target.value)} required />
            </div>

            <div className="input-group">
            <label htmlFor={`education-field-${index}`}>Field of Study *</label>
            <input id={`education-field-${index}`} type="text" placeholder="Computer Science and Engineering" name="field" maxLength={60}
              value={edu.field} onChange={(e) => updateEducation(index, "field", e.target.value)} />
            </div>
            </div>

            <div className="input-row">
            <div className="input-group">
            <label htmlFor={`education-gpa-${index}`}>GPA</label>
            <input id={`education-gpa-${index}`} type="text" placeholder="8.7 / 10" name="gpa" maxLength={10}
              value={edu.gpa} onChange={(e) => updateEducation(index, "gpa", e.target.value)} />
            </div>

            <div className="input-group">
            <label>Graduation Date</label>
            <div style={{ display: "flex", gap: "10px" }}>
              <MonthSelect value={edu.gradMonth} name="gradMonth"
                onChange={(e) => updateEducation(index, "gradMonth", e.target.value)} />
              <YearSelect value={edu.gradYear} name="gradYear"
                onChange={(e) => updateEducation(index, "gradYear", e.target.value)} />
            </div>
            </div>
            </div>

            <button type="button" className="delete-btn" onClick={() => removeEducation(index)}>Delete Education</button>
            <hr />
          </div>
        ))}

        <button type="button" className="add-btn" onClick={addEducation}>+ Add Education</button>

        </div>
        </div>
        )}

        {/* ── Experience ── */}
        {step === 3 && (
        <div className="section">
          <div className="form-card">
        <h2>Experience</h2>

        {formData.experience.map((exp, index) => (
          <div key={index}>
            <div style={{ position: "relative" }}>

            <label htmlFor={`experience-title-${index}`}>Job Title *</label>
            <input
              id={`experience-title-${index}`}
              type="text"
              placeholder="Software Engineer"
              maxLength={50}
              name="title"
              value={exp.title}
              onBlur={() => setTimeout(() => setActiveExpDropdown(null), 150)}
              onChange={(e) => {
                const value = e.target.value;
                updateExperience(index, "title", value);
                if (value.length >= 2) {
                  fetchExperienceSuggestions(value, index);
                } else {
                  setActiveExpDropdown(null);
                }
              }}
            />
              {activeExpDropdown === index &&
                expSuggestions[index] &&
                expSuggestions[index].length > 0 && (
                  <ul className="dropdown">
                    {expSuggestions[index].map((item, i) => (
                      <li
                        key={i}
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => {
                          updateExperience(index, "title", item.title);
                          updateExperience(index, "onet_code", item.onet_code);
                          setActiveExpDropdown(null);
                        }}
                      >
                        {item.title}
                      </li>
                    ))}
                  </ul>
              )}
            </div>

            <div className="input-row">
            <div className="input-group">
            <label htmlFor={`experience-employer-${index}`}>Employer *</label>
            <input id={`experience-employer-${index}`} type="text" placeholder="Innovatech Systems Pvt. Ltd." maxLength={60} name="employer"
              value={exp.employer} onChange={(e) => updateExperience(index, "employer", e.target.value)} />
            </div>

            <div className="input-group">
            <label htmlFor={`experience-location-${index}`}>Location</label>
            <input id={`experience-location-${index}`} type="text" placeholder="Bangalore, India" maxLength={50} name="location"
              value={exp.location} onChange={(e) => updateExperience(index, "location", e.target.value)} />
            </div>
            </div>

            <div className="input-row">
            <div className="input-group">
            <label>Start Date</label>
            <div style={{ display: "flex", gap: "10px" }}>
              <MonthSelect value={exp.startMonth}
                onChange={(e) => updateExperience(index, "startMonth", e.target.value)} />
              <YearSelect value={exp.startYear}
                onChange={(e) => updateExperience(index, "startYear", e.target.value)} />
            </div>
            </div>

            <div className="input-group">
            <label>End Date</label>
            <div style={{ display: "flex", gap: "10px" }}>
              <MonthSelect value={exp.endMonth} disabled={exp.current}
                onChange={(e) => updateExperience(index, "endMonth", e.target.value)} />
              <YearSelect value={exp.endYear} startYear={2026} disabled={exp.current}
                onChange={(e) => updateExperience(index, "endYear", e.target.value)} />
            </div>
            </div>
            <div className="checkbox-group">
            <label htmlFor={`experience-current-${index}`}>Currently Working</label>
            <input id={`experience-current-${index}`} type="checkbox" checked={exp.current} name="current"
                onChange={(e) => updateExperience(index, "current", e.target.checked)} />
            </div>
            </div>

            <label htmlFor={`experience-description-${index}`}>Description</label>
            <textarea
              id={`experience-description-${index}`}
              placeholder="Describe your responsibilities, achievements, and impact..."
              rows="4" maxLength={400}
              style={{ width: "100%" }} name="description"
              value={exp.description} 
              onChange={(e) => updateExperience(index, "description", e.target.value)}
            />

            <div style={{ textAlign: "right", fontSize: "0.85rem",
              color: (exp.description?.length || 0) > 300 ? "#e63946" : "#666",
              fontWeight: (exp.description?.length || 0) > 300 ? "bold" : "normal"
            }}>
              {(exp.description?.length || 0)} / 400
            </div>

            <div className="enhance-btn"> 
              {exp.description?.trim() && (
                <button type="button" onClick={() => handleEnhance(index)} className="gen-btn">
                  Enhance Experience
                </button>
              )}
              {exp.originalDescription &&
              exp.description !== exp.originalDescription && (
                <button
                  type="button"
                  onClick={() => handleResetExperience(index)}
                  className="reset"
                >
                  Reset
                </button>
              )}
            </div>
            <br />

            <button type="button" className="delete-btn" onClick={() => removeExperience(index)}>Delete Experience</button>
            <hr />
          </div>
        ))}

        <button type="button" className="add-btn" onClick={addExperience}>+ Add Experience</button>

        </div>
        </div>
        )}

        {/* ── Skills ── */}
        {step === 4 && (
        <div className="section">
          <div className="form-card">
        <h2>Skills</h2>
      
        <div className="skills-container">

        <div className="skills-left">
        <p style={{ fontSize: "0.82rem", color: "#666", marginTop: "-6px", marginBottom: "10px" }}>
                Please add your most relevant domain-specific skills first, followed by any additional skills.
              </p>
        {formData.skills.map((skill, index) => (
          <div key={index} style={{ display: "flex", gap: "10px" }}>
            <input
              type="text"
              placeholder="Skill"
              value={skill} name="skill" maxLength={80}
              onChange={(e) => updateSkill(index, e.target.value)}
            />
            <button type="button" className="delete-icon-btn" onClick={() => removeSkill(index)}>
              X
            </button>
          </div>
        ))}

        <button type="button" className="add-btn" onClick={addSkill}>+ Add Skill</button>
        </div>

        <div className="skills-right">

          {formData.personal.profession && !skillJobInput ? (
            <>
              <h4>Suggested Skills for <em>{formData.personal.profession}</em></h4>
              <p style={{ fontSize: "0.82rem", color: "#666", marginTop: "-6px", marginBottom: "10px" }}>
                Based on your profession. Search below to use a different job title.
              </p>
              <div className="occupation-wrapper">
                <input
                  type="text"
                  placeholder="Override: search a different job title"
                  value={skillJobInput}
                  onChange={(e) => handleSkillJobChange(e.target.value)}
                  onBlur={() => setTimeout(() => setShowSkillDropdown(false), 150)}
                  className="skill-search-input"
                />
                {showSkillDropdown && skillSuggestions.length > 0 && (
                  <div className="dropdown">
                    {skillSuggestions.map((occ, i) => (
                      <div key={i} className="dropdown-item"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => handleSkillSelect(occ)}>
                        {occ.title}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <h4>{skillJobInput ? <>Suggested Skills for <em>{skillJobInput}</em></> : "Suggested Skills"}</h4>
              {!skillJobInput && (
                <p style={{ fontSize: "0.82rem", color: "#666", marginTop: "-6px", marginBottom: "10px" }}>
                  No profession selected. Search a job title to get suggestions.
                </p>
              )}
              <div className="occupation-wrapper">
                <input
                  type="text"
                  placeholder="Enter job title (e.g., System Administrator)"
                  value={skillJobInput}
                  onChange={(e) => handleSkillJobChange(e.target.value)}
                  onBlur={() => setTimeout(() => setShowSkillDropdown(false), 150)}
                  className="skill-search-input"
                />
                {showSkillDropdown && skillSuggestions.length > 0 && (
                  <div className="dropdown">
                    {skillSuggestions.map((occ, i) => (
                      <div key={i} className="dropdown-item"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => handleSkillSelect(occ)}>
                        {occ.title}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          <div className="skills" style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
            {suggestedSkills.map((skill, i) => {
              const alreadyAdded = formData.skills.includes(skill);
              return (
                <button key={i} type="button"
                  className={`suggested-skill-btn ${alreadyAdded ? "added" : ""}`}
                  disabled={alreadyAdded}
                  onClick={() => {
                    if (!alreadyAdded) {
                     setFormData(prev => ({ ...prev, skills: [...prev.skills, skill] }));
                     }
                  }}>
                  {alreadyAdded ? "✓ " : "+ "}{skill}
                </button>
              );
            })}
          </div>

        </div>

        </div>
        </div>
        </div>
        )}

        {/* ── Projects ── */}
        {step === 5 && (
        <div className="section">
        <div className="form-card">
        <h2>Projects</h2>

        {formData.projects.map((proj, index) => (
          <div key={index}>

            <label htmlFor={`project-title-${index}`}>Title *</label>
            <input id={`project-title-${index}`} type="text" placeholder="TaskFlow – Team Task Management System" maxLength={80} name="title"
              value={proj.title} onChange={(e) => updateProject(index, "title", e.target.value)} />

            <label htmlFor={`project-description-${index}`}>Description *</label>
            <textarea id={`project-description-${index}`} placeholder="TaskFlow is a web-based task management application designed to help teams organize, assign, and track project tasks efficiently." rows="3" style={{ width: "100%" }} maxLength={800} name="description"
              value={proj.description} onChange={(e) => updateProject(index, "description", e.target.value)} />
            <div style={{ textAlign: "right", fontSize: "0.85rem",
              color: (proj.description?.length || 0) > 700 ? "#e63946" : "#666",
              fontWeight: (proj.description?.length || 0) > 700 ? "bold" : "normal"
             }}>
              {(proj.description?.length || 0)} / 800
            </div>
            <div className="input-row">
            <div className="input-group">
            <label htmlFor={`project-role-${index}`}>Role</label>
            <input id={`project-role-${index}`} type="text" placeholder="Backend Developer" maxLength={30} name="role"
              value={proj.role} onChange={(e) => updateProject(index, "role", e.target.value)} />
            </div>

            <div className="input-group">
            <label htmlFor={`project-tools-${index}`}>Tools & Technologies</label>
            <input id={`project-tools-${index}`} type="text" placeholder="Angular, Python, Django" maxLength={200} name="tools"
              value={proj.tools} onChange={(e) => updateProject(index, "tools", e.target.value)} />
            </div>
            </div>

            <label htmlFor={`project-url-${index}`}>Project URL (optional)</label>
            <input id={`project-url-${index}`} type="url" placeholder="https://gitlab.com/yourusername/taskflow-management" maxLength={100} name="url"
              value={proj.url} onChange={(e) => updateProject(index, "url", e.target.value)} />

            <button type="button" className="delete-btn" onClick={() => removeProject(index)}>Delete Project</button>
            <hr />
          </div>
        ))}

        <button type="button" className="add-btn" onClick={addProject}>+ Add Project</button>

        </div>
        </div>
        )}

        {/* ── Certifications & Achievements ── */}
        {step === 6 && (
        <div className="section">
        <div className="form-card">
        <h2>Certifications &amp; Achievements</h2>

        {formData.certifications.map((cert, index) => (
          <div key={index}>

            <label htmlFor={`certification-name-${index}`}>Certification / Achievement Name *</label>
            <input id={`certification-name-${index}`} type="text" placeholder="AWS Certified Cloud Practitioner" maxLength={80} name="name"
              value={cert.name} onChange={(e) => updateCertification(index, "name", e.target.value)} />

            <label htmlFor={`certification-org-${index}`}>Issuing Organisation</label>
            <input id={`certification-org-${index}`} type="text" placeholder="Amazon Web Services (AWS)" maxLength={60} name="issuingorg"
              value={cert.issuingOrg} onChange={(e) => updateCertification(index, "issuingOrg", e.target.value)} />

            <div className="input-row">
            <div className="input-group">
            <label htmlFor={`certification-date-${index}`}>Date Achieved</label>
            <input id={`certification-date-${index}`} type="text" placeholder="e.g. Mar 2024" maxLength={20} name="achievedDate"
              value={cert.achievedDate} onChange={(e) => updateCertification(index, "achievedDate", e.target.value)} />
            </div>

            <div className="input-group">
            <label htmlFor={`certification-url-${index}`}>Credential URL (optional)</label>
            <input id={`certification-url-${index}`} type="url" placeholder="https://example.com/credential" maxLength={100} name="url"
              value={cert.url} onChange={(e) => updateCertification(index, "url", e.target.value)} />
            </div>
            </div>

            <button type="button" className="delete-btn" onClick={() => removeCertification(index)}>Delete Certification</button>
            <hr />
          </div>
        ))}

        <button type="button" className="add-btn" onClick={addCertification}>+ Add Certification / Achievement</button>

        </div>
        </div>
        )}

        {/* ── Languages ── */}
        {step === 7 && (
        <div className="section">
          <div className="form-card">
        <h2>Languages</h2>

        {formData.languages.map((lang, index) => (
          <div key={index}>
            <input type="text" placeholder="Language (e.g. English)" maxLength={30}
              value={lang.name} onChange={(e) => updateLanguage(index, "name", e.target.value)} />

            <select value={lang.level} name="level" onChange={(e) => updateLanguage(index, "level", e.target.value)}>
              <option value="Beginner">Beginner</option>
              <option value="Elementary">Elementary</option>
              <option value="Intermediate">Intermediate</option>
              <option value="Upper Intermediate">Upper Intermediate</option>
              <option value="Advanced">Advanced</option>
              <option value="Native">Native / Bilingual</option>
            </select>

            <button type="button" className="delete-btn" onClick={() => removeLanguage(index)}>Delete</button>
            <hr />
          </div>
        ))}

        <button type="button" className="add-btn" onClick={addLanguage}>+ Add Language</button>

        </div>
        </div>
        )}

        {/* ── Template & Actions ── */}
        {step === 1 && (
        <div className="section">
        <div className="form-card">
          <h3>Select Resume Template</h3>

          <div className="template-grid">
            {[
              "classic", "twocolumn", "ats", "corporate", "modern",
              "creative", "sidebar", "minimal", "timeline",
              "academic", "striped", "pastel", "warm",
              "technical", "typographic", "architect", "bold"
            ].map((tpl) => {
              const TEMPLATE_TOAST_ID = "template-toast";
              const formattedName = tpl.replace(/^\w/, c => c.toUpperCase());

              return (
                <div
                  key={tpl}
                  className={`template-wrapper ${
                    formData.template === tpl ? "active-template" : ""
                  }`}
                  onClick={() => {
                    if (formData.template !== tpl) {
                      setFormData(prev => ({ ...prev, template: tpl }));
                      if (toast.isActive(TEMPLATE_TOAST_ID)) {
                        toast.update(TEMPLATE_TOAST_ID, {
                          render: `${formattedName} template selected`,
                          autoClose: 1000,
                        });
                      } else {
                        toast.info(`${formattedName} template selected`, {
                          toastId: TEMPLATE_TOAST_ID,
                          autoClose: 1000,
                          hideProgressBar: true,
                        });
                      }
                    }
                  }}
                >
                  <div className="template-card">
                    <img src={`/templates/${tpl}.png`} alt={formattedName} />
                    {formData.template === tpl && (
                      <div className="template-check">✓</div>
                    )}
                  </div>
                  <div className="template-name">{formattedName}</div>
                </div>
              );
            })}
          </div>

        </div>
      </div>
        )}

        <div className="step-navigation">
          {step > 0 && (
            <button type="button" onClick={prevStep}>
              ← Previous
            </button>
          )}

          {step < totalSteps && (
            <button type="button" onClick={nextStep}>
              Continue →
            </button>
          )}
        </div>

        <div className="bottom-step-bar">
          {steps.map((label, index) => (
            <div
              key={index}
              className={`step-circle ${step === index ? "active-step" : ""}`}
              onClick={() => setStep(index)}
              title={label}
            >
              {index + 1}
            </div>
          ))}
        </div>

      </div>


      <div className="preview-section">
        <div className="preview-wrapper">
        <div className="preview-header">
        <h2>Preview</h2>

        <button
          className="ap-btn"
          onClick={() => setShowJobMatch(!showJobMatch)}
        >
          {showJobMatch ? "Hide Job Match" : "Check Job Match"}
        </button>

        <button
          className={`analytics-btn ${analytics ? (analytics.resume_score >= 70 ? "analytics-btn-green" : analytics.resume_score >= 40 ? "analytics-btn-amber" : "analytics-btn-red") : ""}`}
          onClick={() => setShowAnalytics(!showAnalytics)}
        >
          {showAnalytics ? "✕ Close" : "📊 Analytics"}
          {analytics && (
            <span className="analytics-score-badge">{analytics.resume_score}</span>
          )}
        </button>
        </div>

        {showJobMatch && (
          <div className="analytics-panel">

            <div className="ap-section-title">Job Match Analysis</div>

            <div className="jm-input">
              <textarea
                placeholder="Paste job description..."
                value={jobText} id="autoResizeTextarea"
                onChange={(e) => setJobText(e.target.value)}
              />
              <button className="analyze-btn" onClick={handleJobMatch}>
                Analyze
              </button>
            </div>

            {jobMatch && (
              <div className="jm-grid">

                {/* SCORE CARD */}
                <div className="jm-card score-card">
                  <h3>Match Score</h3>
                  <div className="score-value">{jobMatch.job_match_score}%</div>
                  <div className={`fit-badge ${jobMatch.fit_level.toLowerCase().replace(" ","-")}`}>
                    {jobMatch.fit_level}
                  </div>
                  <br/>
                  <button
                    className="update-match-btn"
                    onClick={handleJobMatch}
                  >
                    Update Match
                  </button>
                  <br/>
                  {matchOutdated && (
                    <p className="match-warning">
                      Resume updated — click Update Match
                    </p>
                  )}
                  </div>
                  

              

                {/* MISSING SKILLS */}
                <div className="jm-card">
                  <h3>Missing Skills</h3>

                  <div className="skill-list">
                    {jobMatch.missing_skills?.map((s,i)=>(
                      <span className="skill-pill" key={i}>{s}</span>
                    ))}
                  </div>
                </div>

                {/* SUGGESTIONS */}
                <div className="jm-card">
                  <h3>Suggestions</h3>

                  {jobMatch.recommendations?.map((r,i)=>(
                    <div className="suggestion" key={i}>
                      {r.message}
                    </div>
                  ))}
                </div>

              </div>
            )}

          </div>
        )}

        {showAnalytics && analytics && (
          <div className="analytics-panel">

            {/* ══ SCORE HEADER ══════════════════════════════════════════════ */}
            <div className="ap-hero">
              <div className="ap-ring-wrap">
                <svg viewBox="0 0 120 120" width="120" height="120">
                  <circle cx="60" cy="60" r="50" fill="none" stroke="#f0f0f0" strokeWidth="12"/>
                  <circle cx="60" cy="60" r="50" fill="none"
                    stroke={analytics.resume_score >= 70 ? "#22c55e" : analytics.resume_score >= 40 ? "#f59e0b" : "#ef4444"}
                    strokeWidth="12"
                    strokeDasharray={`${(analytics.resume_score / 100) * 314} 314`}
                    strokeLinecap="round"
                    transform="rotate(-90 60 60)"
                    style={{transition:"stroke-dasharray 0.6s ease"}}
                  />
                </svg>
                <div className="ap-ring-inner">
                  <span className="ap-score-num">{analytics.resume_score}</span>
                  <span className="ap-score-sub">/ 100</span>
                </div>
              </div>
              <div className="ap-hero-right">
                <div className="ap-grade" style={{color: analytics.resume_score >= 70 ? "#16a34a" : analytics.resume_score >= 40 ? "#d97706" : "#dc2626"}}>
                  {analytics.resume_score >= 85 ? "Excellent" : analytics.resume_score >= 70 ? "Good" : analytics.resume_score >= 50 ? "Fair" : analytics.resume_score >= 30 ? "Weak" : "Poor"}
                </div>
                <div className="ap-grade-sub">Overall Resume Score</div>
                <div className="ap-contact-strip">
                  <span className={analytics.has_email ? "ap-dot ap-dot-ok" : "ap-dot ap-dot-bad"}>
                    {analytics.has_email ? "✓" : "✗"} Email
                  </span>
                  <span className={analytics.has_phone ? "ap-dot ap-dot-ok" : "ap-dot ap-dot-bad"}>
                    {analytics.has_phone ? "✓" : "✗"} Phone
                  </span>
                  <span className={analytics.has_linkedin ? "ap-dot ap-dot-ok" : "ap-dot ap-dot-bad"}>
                    {analytics.has_linkedin ? "✓" : "✗"} LinkedIn
                  </span>
                </div>
              </div>
            </div>

            {/* ══ STAT TILES ════════════════════════════════════════════════ */}
            <div className="ap-tiles">
              {[
                { icon: "📝", val: analytics.word_count,             label: "Words" },
                { icon: "📄", val: analytics.estimated_pages,        label: "Pages" },
                { icon: "🛠",  val: analytics.skills_count,           label: "Skills" },
                { icon: "💼", val: analytics.experience_entries,     label: "Jobs" },
                { icon: "🎯", val: analytics.quantified_achievements, label: "Metrics" },
              ].map(({ icon, val, label }) => (
                <div className="ap-tile" key={label}>
                  <span className="ap-tile-icon">{icon}</span>
                  <span className="ap-tile-val">{val}</span>
                  <span className="ap-tile-label">{label}</span>
                </div>
              ))}
            </div>

            {/* ══ SCORE BREAKDOWN ════════════════════════════════════════════ */}
            <div className="ap-section">
              <div className="ap-section-title">Score Breakdown</div>
              <div className="ap-bars">
                {[
                  { label: "Completeness",      pct: analytics.completeness_score,                        display: `${analytics.completeness_score}%`,  color: "#6366f1" },
                  { label: "Action Verbs",       pct: Math.min(analytics.action_verbs_used / 10, 1) * 100,  display: `${analytics.action_verbs_used} / 10`, color: "#0ea5e9" },
                  { label: "ATS Keywords",       pct: Math.min(analytics.keywords_count / 10, 1) * 100,     display: `${analytics.keywords_count} / 10`,   color: "#8b5cf6" },
                  { label: "Quantified Results", pct: Math.min(analytics.quantified_achievements / 5, 1) * 100, display: `${analytics.quantified_achievements} / 5`, color: "#f59e0b" },
                  { label: "Content Depth",      pct: Math.min(analytics.word_count / 400, 1) * 100,        display: `${analytics.word_count} words`,      color: "#22c55e" },
                ].map(({ label, pct, display, color }) => (
                  <div className="ap-bar-row" key={label}>
                    <span className="ap-bar-label">{label}</span>
                    <div className="ap-bar-track">
                      <div className="ap-bar-fill" style={{ width: `${pct}%`, background: color }}/>
                    </div>
                    <span className="ap-bar-val">{display}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="ap-section">
              <div className="ap-ats-score-box">
                <div className="ap-ats-score">{analytics.ats_score}</div>
                <div className="ap-ats-label"><h2>ATS Compatibility Score</h2></div>
              </div>


              <div className="ap-mini-grid">
                {[ 
                  { label: "Keywords", val: analytics?.ats_breakdown?.keyword_alignment },
                  { label: "Context", val: analytics?.ats_breakdown?.keyword_context },
                  { label: "Metrics", val: analytics?.ats_breakdown?.quantified_results },
                  { label: "Format", val: analytics?.ats_breakdown?.formatting },
                  { label: "Sections", val: analytics?.ats_breakdown?.sections },
                  { label: "File", val: analytics?.ats_breakdown?.file_type }
                ].map(({ label, val }) => {

                  const color =
                    val >= 80 ? "#22c55e" :
                    val >= 50 ? "#f59e0b" :
                    "#ef4444";

                  const circumference = 2 * Math.PI * 18;
                  const dash = (val / 100) * circumference;

                  return (
                    <div className="ap-mini-ring" key={label}>
                      <svg width="45" height="45" viewBox="0 0 45 45">
                        <circle
                          cx="22.5"
                          cy="22.5"
                          r="18"
                          stroke="#e5e7eb"
                          strokeWidth="4"
                          fill="none"
                        />
                        <circle
                          cx="22.5"
                          cy="22.5"
                          r="18"
                          stroke={color}
                          strokeWidth="4"
                          fill="none"
                          strokeDasharray={`${dash} ${circumference}`}
                          strokeLinecap="round"
                          transform="rotate(-90 22.5 22.5)"
                        />
                      </svg>

                      <span className="ap-mini-score">{val}</span>
                      <span className="ap-mini-label">{label}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ══ KEYWORDS ═══════════════════════════════════════════════════ */}
            {/*
            <div className="ap-section">
              <div className="ap-section-title">Tech Keywords Detected ({analytics.keywords_count})</div>
              {analytics.keywords_found.length > 0 ? (
                <div className="ap-chips">
                  {analytics.keywords_found?.map((kw, i) => (
                    <span key={i} className="ap-chip ap-chip-blue">{kw}</span>
                  ))}
                </div>
              ) : (
                <p className="ap-empty">No tech keywords found — add languages, tools and frameworks.</p>
              )}
            </div>
            */}

            {/* ══ MISSING SECTIONS ═══════════════════════════════════════════ */}
            {analytics.missing_sections.length > 0 && (
              <div className="ap-section">
                <div className="ap-section-title">Missing Sections</div>
                <div className="ap-chips">
                  {analytics.missing_sections?.map((s, i) => (
                    <span key={i} className="ap-chip ap-chip-amber">{s}</span>
                  ))}
                </div>
              </div>
            )}

            {/* ══ SUGGESTIONS ════════════════════════════════════════════════ */}
            <div className="ap-section">
              <div className="ap-section-title">Suggestions to Improve</div>
              <div className="ap-suggestions">
                {analytics.suggestions?.map((s, i) => (
                  <div key={i} className={`ap-sug ap-sug-${s.type}`}>
                    <span className="ap-sug-icon">
                      {s.type === "error" ? "✕" : s.type === "warn" ? "⚠" : s.type === "success" ? "✓" : "ℹ"}
                    </span>
                    <span className="ap-sug-text">{s.text}</span>
                  </div>
                ))}
              </div>
            </div>

          </div>
        )}



        <div className="preview-container">
          {previewHTML ? (
            <div
              id="resume-preview"
              className="preview-content"
              dangerouslySetInnerHTML={{ __html: previewHTML }}
            />
          ) : (
            <div className="preview-placeholder">
              No preview yet. Submit the form.
            </div>
          )}
        </div>
        </div>
      </div>

    </div>
  );
}

export default ResumeForm;